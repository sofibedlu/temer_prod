# -*- coding: utf-8 -*-
# Wing Distribution - Assignment algorithm code
# File: wing_distribution_configuration/models/crm_reception_inherit.py
# This file contains only the algorithm logic for reference/sharing (no Odoo model inheritance).

import logging
import random

_logger = logging.getLogger(__name__)


# ============ 1. CREATE: when assignment is triggered ============
# Called when crm.reception record is created.

def create_assignment_logic(rec):
    """
    Run on each new reception record.
    If active walk-in distribution exists: pick next user by weighted team and assign.
    """
    if rec._has_active_walkin_distribution_lines():
        allowed_users = rec._get_active_walkin_users()
        if not rec.nominated_salesperson_id or rec.nominated_salesperson_id not in allowed_users:
            user, config = rec._get_next_user_by_weighted_team()
            if user:
                rec.write({
                    "nominated_salesperson_id": user.id,
                    "nominated_wing_id": config.id if config else False,
                    "assigned_via_wing_distribution": True,
                })
    if not rec.assigned_salesperson_id and rec.nominated_salesperson_id:
        rec.write({
            "assigned_salesperson_id": rec.nominated_salesperson_id.id,
            "assigned_wing_id": rec.nominated_wing_id.id if rec.nominated_wing_id else False,
        })


# ============ 2. CORE ALGORITHM: weighted team selection ============

def _get_next_user_by_weighted_team(self):
    """
    Pick next user by:
    1) Get walk-in distribution type and active lines
    2) If all lines 'served', reset and start new round
    3) Group lines by wing, compute weight per wing (count/total)
    4) Among wings not yet 'served', pick one with max weight; tie-break by sequence (last_wing param)
    5) Pick one random user from that wing's remaining lines, mark line and wing as 'served'
    6) Return (user, wing_config)
    """
    DistributionType = self.env["wing.distribution.type"]
    DistributionLine = self.env["wing.distribution.line"]
    TeamState = self.env["wing.distribution.team.state"]

    dist_type = DistributionType.search([("code", "=", "walk_in")], limit=1)
    if not dist_type:
        dist_type = DistributionType.search([("name", "ilike", "walk in")], limit=1)
    if not dist_type:
        _logger.info("Wing Distribution: no walk-in distribution type found.")
        return False, False

    lines = DistributionLine.search(
        [("distribution_type_id", "=", dist_type.id), ("active", "=", True)]
    )
    if not lines:
        _logger.info("Wing Distribution: no active distribution lines.")
        return False, False

    remaining_lines = lines.filtered(lambda l: not l.status)
    if not remaining_lines:
        lines.filtered(lambda l: l.status == "served").write({"status": False})
        self.env["wing.distribution.team.state"].search(
            [("distribution_type_id", "=", dist_type.id)]
        ).write({"status": False})
        remaining_lines = lines.filtered(lambda l: not l.status)
        _logger.info("Wing Distribution cycle complete: reset supervisor and wing statuses.")

    wing_lines_map = {}
    for line in lines:
        if not line.wing_id:
            continue
        wing_lines_map.setdefault(line.wing_id, self.env["wing.distribution.line"])
        wing_lines_map[line.wing_id] |= line

    wing_remaining_map = {}
    for line in remaining_lines:
        if not line.wing_id:
            continue
        wing_remaining_map.setdefault(line.wing_id, self.env["wing.distribution.line"])
        wing_remaining_map[line.wing_id] |= line

    if not wing_lines_map:
        _logger.info("Wing Distribution: active lines have no wing, skipping.")
        return False, False

    total_count = sum(len(wing_lines) for wing_lines in wing_remaining_map.values())
    if not total_count:
        return False, False

    wing_ids = [wing.id for wing in wing_remaining_map.keys()]
    states = TeamState.search(
        [("distribution_type_id", "=", dist_type.id), ("wing_id", "in", wing_ids)]
    )
    state_by_wing = {state.wing_id.id: state for state in states if state.wing_id}

    for wing, wing_lines in wing_remaining_map.items():
        state = state_by_wing.get(wing.id)
        if not state:
            state = TeamState.create({
                "wing_id": wing.id,
                "distribution_type_id": dist_type.id,
            })
            state_by_wing[wing.id] = state
        weight = len(wing_lines) / float(total_count)
        state.write({
            "supervisor_count": len(wing_lines),
            "weight": weight,
            "active": True,
        })

    active_states = [state_by_wing[wing_id] for wing_id in wing_ids if wing_id in state_by_wing]
    candidate_states = [state for state in active_states if not state.status]
    if not candidate_states and active_states:
        TeamState.browse([state.id for state in active_states]).write({"status": False})
        _logger.info("Wing Distribution round complete: reset wing statuses to empty.")
        candidate_states = active_states
    if not candidate_states:
        return False, False

    max_weight = max(state.weight for state in candidate_states)
    top_states = [state for state in candidate_states if state.weight == max_weight]
    chosen_state = self._pick_next_state_by_sequence(top_states, dist_type)
    chosen_wing = None
    for wing in wing_remaining_map.keys():
        if state_by_wing.get(wing.id) and state_by_wing.get(wing.id).id == chosen_state.id:
            chosen_wing = wing
            break
    if not chosen_wing:
        return False, False

    available_lines = wing_remaining_map[chosen_wing]
    if not available_lines:
        chosen_state.write({"status": "served"})
        return False, False

    chosen_line = random.choice(available_lines)
    chosen_line.write({"status": "served"})
    chosen_state.write({"status": "served"})

    config = self._get_walkin_config_for_wing(chosen_wing)

    if active_states and all(state.status == "served" for state in active_states):
        TeamState.browse([state.id for state in active_states]).write({"status": False})
        _logger.info("Wing Distribution round complete: reset wing statuses to empty.")

    return chosen_line.user_id, config


# ============ 3. SEQUENCE: which wing gets next turn ============

def _pick_next_state_by_sequence(self, states, dist_type):
    """Among states with same max weight, pick next by wing id sequence (round-robin)."""
    Param = self.env["ir.config_parameter"].sudo()
    if not states:
        return False
    sorted_states = sorted(states, key=lambda s: s.wing_id.id)
    key = "wing_distribution.last_wing_%s" % dist_type.id
    last_wing_id = int(Param.get_param(key, default="0") or 0)
    if last_wing_id:
        for idx, state in enumerate(sorted_states):
            if state.wing_id.id == last_wing_id:
                next_state = sorted_states[(idx + 1) % len(sorted_states)]
                Param.set_param(key, str(next_state.wing_id.id))
                return next_state
    Param.set_param(key, str(sorted_states[0].wing_id.id))
    return sorted_states[0]


# ============ 4. HELPERS ============

def _get_active_walkin_users(self):
    """Return all users in active walk-in distribution lines."""
    DistributionType = self.env["wing.distribution.type"]
    DistributionLine = self.env["wing.distribution.line"]
    dist_type = DistributionType.search([("code", "=", "walk_in")], limit=1)
    if not dist_type:
        dist_type = DistributionType.search([("name", "ilike", "walk in")], limit=1)
    if not dist_type:
        return self.env["res.users"]
    lines = DistributionLine.search(
        [("distribution_type_id", "=", dist_type.id), ("active", "=", True)]
    )
    return lines.mapped("user_id")


def _has_active_walkin_distribution_lines(self):
    """True if there is at least one active walk-in distribution line."""
    DistributionType = self.env["wing.distribution.type"]
    DistributionLine = self.env["wing.distribution.line"]
    dist_type = DistributionType.search([("code", "=", "walk_in")], limit=1)
    if not dist_type:
        dist_type = DistributionType.search([("name", "ilike", "walk in")], limit=1)
    if not dist_type:
        return False
    return bool(
        DistributionLine.search_count(
            [("distribution_type_id", "=", dist_type.id), ("active", "=", True)]
        )
    )


def _get_walkin_config_for_wing(self, wing):
    """Get property.wing.config for Walk In source and given wing."""
    WingConfig = self.env["property.wing.config"]
    if wing:
        config = WingConfig.search([
            ("source_id.name", "=", "Walk In"),
            ("wing_id", "=", wing.id),
        ], limit=1)
        if config:
            return config
    return WingConfig.search([("source_id.name", "=", "Walk In")], limit=1)
