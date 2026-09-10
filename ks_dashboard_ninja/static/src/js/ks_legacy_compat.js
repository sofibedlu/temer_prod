/** @odoo-module **/
/*
 * ks_dashboard_ninja - Odoo 15 -> 17 compat layer.
 *
 * Odoo 17 removed the whole legacy widget stack this module was built on
 * (odoo.define, AbstractField/AbstractAction, web.field_registry, web.core/qweb,
 * web.session, web.datepicker, web.searchUtils, ...).  This file re-provides the
 * subset of that API surface that the module's method bodies actually use,
 * implemented on top of real Odoo 17 primitives, so that every original method
 * keeps its behaviour (no functional regression).
 *
 * Two widget styles are supported, both producing subclasses of the OWL
 * component `LegacyField`:
 *   - class-style   : `class X extends LegacyField { ... }`  (converted files)
 *   - extend-style  : `var X = AbstractField.extend({ ... })` (files whose body
 *                     is kept byte-for-byte; `.extend` re-creates the Odoo 15
 *                     class machinery, including `this._super` chains)
 *
 * Legacy field widgets are emulated through `LegacyField` (an OWL Component):
 *  - props = standardFieldProps (record / name / readonly)
 *  - this.$el  -> jQuery wrapper of the component root
 *  - this.$    -> this.$el.find(...)
 *  - this.value      -> props.record.data[props.name]
 *  - this.mode       -> 'readonly' | 'edit'
 *  - this.recordData -> props.record.data
 *  - this.name       -> props.name
 *  - this._setValue(v) -> props.record.update({name: v})
 *  - this._render()  -> called whenever the widget must (re)draw itself
 *  - this.events     -> hash of delegated events, bound on each draw
 *  - this.resetOnAnyFieldChange -> re-draw on every record change
 */

import { Component, xml } from "@odoo/owl";
import { useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { renderToString } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { getCurrency } from "@web/core/currency";
import { url } from "@web/core/utils/urls";
import { formatFloat, formatInteger, formatMonetary, formatDateTime } from "@web/views/fields/formatters";
import { parseFloat } from "@web/views/fields/parsers";

// ---------------------------------------------------------------------------
// on-screen error banner (debug aid, no console needed)
// ---------------------------------------------------------------------------
function _ksShowBanner(title, detail) {
    try {
        let el = document.getElementById("ks_tpl_err");
        if (!el) {
            el = document.createElement("div");
            el.id = "ks_tpl_err";
            el.style.cssText =
                "position:fixed;left:0;top:0;right:0;background:#c00;color:#fff;" +
                "z-index:999999;padding:10px;font:13px monospace;white-space:pre-wrap;";
            document.body.appendChild(el);
        }
        el.textContent = title + "\n" + String(detail || "");
    } catch (e) {
        /* never mind */
    }
}

// debug: who mounted / failed (readable via window.__ksWidgetLog)
function _ksLogWidget(name, state, detail) {
    try {
        const w = window;
        w.__ksWidgetLog = w.__ksWidgetLog || [];
        w.__ksWidgetLog.push({
            name: name || "?",
            state: state || "?",
            detail: String((detail && (detail.message || detail)) || "").slice(0, 500),
            time: Date.now(),
        });
    } catch (e) {
        /* never mind */
    }
}

// ---------------------------------------------------------------------------
// core.qweb.render(name, ctx) -> HTML string  (was web.core)
// ---------------------------------------------------------------------------
const qweb = {
    render(template, context = {}) {
        try {
            // Odoo 15 injected legacy globals (underscore) into the QWeb
            // context; Odoo 17's renderToString does not.  Re-inject them so
            // the untouched templates (which call _(...) ) keep working.
            const ctx = Object.assign({}, context || {});
            if (typeof ctx._ !== "function") {
                ctx._ = (typeof window !== "undefined" && window._) || undefined;
            }
            return renderToString(template, ctx);
        } catch (error) {
            const msg = String((error && error.message) || error);
            window.__ksTemplateError = { template, message: msg };
            console.error("ks qweb render failed on template: " + template, error);
            _ksShowBanner("TEMPLATE FAIL: " + template, msg);
            throw error;
        }
    },
};

// ---------------------------------------------------------------------------
// field_utils (subset used by the module)
// ---------------------------------------------------------------------------
const field_utils = {
    format: {
        float(value, _opts, digits) {
            return formatFloat(value, digits || {});
        },
        integer(value) {
            return formatInteger(value, {});
        },
        monetary(value, currency) {
            if (currency && currency.symbol) {
                return formatMonetary(value, { currency });
            }
            return formatFloat(value, {});
        },
        datetime(value, _opts, opts) {
            // legacy: format.datetime(moment(...), {}, {timezone: false})
            return formatDateTime(value, { timezone: opts && opts.timezone === false ? "utc" : "local" });
        },
    },
    parse: {
        float(value) {
            if (value === false || value === undefined || value === "") {
                return false;
            }
            const parsed = parseFloat(value);
            return isNaN(parsed) ? false : parsed;
        },
    },
};

// ---------------------------------------------------------------------------
// time (was web.time) -- only strftime_to_moment_format is used
// ---------------------------------------------------------------------------
const time = {
    strftime_to_moment_format(fmt) {
        if (!fmt) {
            return "YYYY-MM-DD HH:mm:ss";
        }
        const s = String(fmt);
        // already moment-style (no %-directives): pass through
        if (!s.includes("%")) {
            return s;
        }
        return s
            .replace(/%Y|%y/g, "YYYY")
            .replace(/%m/g, "MM")
            .replace(/%d/g, "DD")
            .replace(/%H/g, "HH")
            .replace(/%M/g, "mm")
            .replace(/%S/g, "ss")
            .replace(/%p/g, "A")
            .replace(/%-?[a-zA-Z]/g, "");
    },
};

// ---------------------------------------------------------------------------
// session (subset used by the module)
// ---------------------------------------------------------------------------
const ksSession = {
    get uid() {
        return session.uid !== undefined ? session.uid : false;
    },
    get user_id() {
        return session.uid;
    },
    get user_context() {
        return session.user_context || {};
    },
    get partner_id() {
        return session.partner_id;
    },
    get company_id() {
        return session.company_id;
    },
    get_currency(currency_id) {
        const cur = currency_id && getCurrency(currency_id);
        if (cur) {
            return { symbol: cur.symbol, position: cur.position };
        }
        return false;
    },
    // legacy session.url(path, params) -> full URL string
    url(path, params) {
        return url(path, params);
    },
    // legacy session.get_file({url, data, complete, error}) - downloads a file
    // produced by a POST endpoint (used by the JSON/export flows)
    get_file(options) {
        const opts = options || {};
        // Odoo 17 keeps the CSRF token on the global `odoo` object
        // (window.odoo.csrf_token) - core's own download/file_upload code
        // reads it from there.  `session.csrf_token` no longer exists in 17,
        // so fall back to it only if the global is unavailable.
        const csrf =
            (typeof window !== "undefined" && window.odoo && window.odoo.csrf_token) ||
            session.csrf_token ||
            "";
        const body = new URLSearchParams(opts.data || {});
        // Odoo 17 CSRF check also accepts the token as a form field - send it
        // both ways so the export download is never rejected with a 400.
        body.set("csrf_token", csrf);
        fetch(opts.url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-CSRF-Token": csrf,
            },
            body: body.toString(),
        })
            .then((resp) => {
                if (!resp.ok) {
                    throw new Error("HTTP " + resp.status);
                }
                return resp.blob();
            })
            .then((blob) => {
                const a = document.createElement("a");
                const objUrl = window.URL.createObjectURL(blob);
                a.href = objUrl;
                a.download = "dashboard_ninja.json";
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(objUrl);
                if (typeof opts.complete === "function") {
                    opts.complete();
                }
            })
            .catch((err) => {
                if (typeof opts.complete === "function") {
                    opts.complete();
                }
                if (typeof opts.error === "function") {
                    opts.error(err);
                }
            });
    },
};

// ---------------------------------------------------------------------------
// legacy class machinery (.extend / .include / this._super)
// ---------------------------------------------------------------------------
function _installMixin(proto, mixin) {
    for (const key of Object.keys(mixin)) {
        const val = mixin[key];
        if (typeof val === "function") {
            const parentFn = proto[key];
            proto[key] = function (...args) {
                const prevSuper = this._super;
                this._super = typeof parentFn === "function"
                    ? function (...sargs) { return parentFn.apply(this, sargs); }
                    : function () {};
                try {
                    return val.apply(this, args);
                } finally {
                    if (prevSuper === undefined) {
                        delete this._super;
                    } else {
                        this._super = prevSuper;
                    }
                }
            };
        } else {
            proto[key] = val;
        }
    }
}

function _makeExtendable(Cls) {
    Cls.extend = function (props) {
        const Sub = class extends Cls {};
        _installMixin(Sub.prototype, props);
        return Sub;
    };
    Cls.include = function (props) {
        _installMixin(Cls.prototype, props);
        return Cls;
    };
    return Cls;
}

// ---------------------------------------------------------------------------
// Legacy field widget base (OWL emulation of Odoo 15 AbstractField)
// ---------------------------------------------------------------------------
export class LegacyField extends Component {
    // Host div: the legacy _render() bodies inject the widget content into this
    // root themselves (jQuery style), exactly like Odoo 15 AbstractField did.
    static template = xml`<div t-ref="root" class="o_field_widget"/>`;
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.rootRef = useRef("root");
        this._lastValue = undefined;
        this._renderQueued = false;
        _ksLogWidget(this.props && this.props.name, "mount");
        // extend-style subclasses declare `init(parent, state, params)`; invoke
        // the whole legacy init chain (with _super) before the first render.
        if (typeof this.init === "function") {
            this.init(undefined, undefined, undefined);
        }
        // keep display in sync with the underlying record
        useRecordObserver(() => {
            if (this.resetOnAnyFieldChange) {
                this._scheduleRender();
            } else {
                const value = this.props.record.data[this.props.name];
                if (value !== this._lastValue) {
                    this._scheduleRender();
                }
            }
        });
        onMounted(() => {
            _ksLogWidget(this.props && this.props.name, "onMounted root=" + !!this._root);
            this._doRender();
        });
        onPatched(() => {
            _ksLogWidget(this.props && this.props.name, "onPatched root=" + !!this._root);
            this._doRender();
        });
        onWillUnmount(() => {
            _ksLogWidget(this.props && this.props.name, "unmount");
            if (this._eventsBound) {
                this.$el.off();
                this._eventsBound = false;
            }
        });
    }

    _scheduleRender() {
        if (this._renderQueued) {
            return;
        }
        this._renderQueued = true;
        Promise.resolve().then(() => {
            this._renderQueued = false;
            const root = this._root;
            if (root && root.isConnected) {
                this._doRender();
            }
        });
    }

    // Odoo 17's OWL build does not expose Component.el - the DOM root of a
    // component is only reachable through the t-ref (rootRef).  This getter
    // centralises that access so all legacy render paths use the real root.
    get _root() {
        return this.rootRef ? this.rootRef.el : null;
    }

    _doRender() {
        const root = this._root;
        _ksLogWidget(this.props && this.props.name, "doRender enter root=" + !!root + " renderFn=" + typeof this._render);
        if (!root) {
            return;
        }
        if (this._eventsBound) {
            this.$el.off();
            this._eventsBound = false;
        }
        this.$el.empty();
        if (this.legacyRootClass) {
            root.classList.remove(this.legacyRootClass);
        }
        if (this.legacyTemplate) {
            try {
                const html = renderToString(this.legacyTemplate, { widget: this });
                root.insertAdjacentHTML("beforeend", html);
            } catch (error) {
                console.error("ks_dashboard_ninja legacy template render error", error, this.legacyTemplate);
            }
        }
        if (this.legacyRootClass) {
            root.classList.add(this.legacyRootClass);
        }
        try {
            this._render();
            _ksLogWidget(this.props && this.props.name, "render-ok children=" + this.$el.children().length);
        } catch (error) {
            const msg = String((error && error.stack) || error);
            console.error("ks_dashboard_ninja widget render error", error, this.props && this.props.name);
            _ksLogWidget(this.props && this.props.name, "render-error", error);
            _ksShowBanner("WIDGET FAIL: " + (this.props && this.props.name), msg);
        }
        this._bindEvents();
    }

    _bindEvents() {
        const events = this.events || {};
        for (const key of Object.keys(events)) {
            const idx = key.indexOf(" ");
            const eventName = idx === -1 ? key : key.slice(0, idx);
            const selector = idx === -1 ? undefined : key.slice(idx + 1);
            const handler = events[key];
            if (typeof handler === "function") {
                this.$el.on(eventName, selector, handler.bind(this));
            } else if (typeof this[handler] === "function") {
                this.$el.on(eventName, selector, (ev) => this[handler](ev));
            }
        }
        this._eventsBound = true;
    }

    // --- legacy AbstractField API surface ---------------------------------
    get $el() {
        return $(this.rootRef.el);
    }
    get $() {
        return (selector) => this.$el.find(selector);
    }
    get value() {
        return this.props.record.data[this.props.name];
    }
    get mode() {
        return this.props.readonly ? "readonly" : "edit";
    }
    get readonly() {
        return this.props.readonly;
    }
    get name() {
        return this.props.name;
    }
    get recordData() {
        return this.props.record.data;
    }

    _setValue(value) {
        if (this.props.readonly) {
            return;
        }
        this.props.record.update({ [this.props.name]: value });
    }
}

// default legacy prototype values (so extend-style mixins can rely on them)
LegacyField.prototype.events = {};
LegacyField.prototype.resetOnAnyFieldChange = false;
LegacyField.prototype._render = function () {};
_makeExtendable(LegacyField);

// legacy alias used by extend-style files (require('web.AbstractField'))
export const AbstractField = LegacyField;

// ---------------------------------------------------------------------------
// legacy field registry shim: registry.add('name', Class)
// ---------------------------------------------------------------------------
const fieldRegistry = {
    add(name, cls) {
        const supportedTypes =
            cls.supportedFieldTypes ||
            (cls.prototype && cls.prototype.supportedFieldTypes) ||
            undefined;
        registry.category("fields").add(name, {
            component: cls,
            supportedTypes,
        });
    },
};

// core shim exposing the legacy `core.qweb` shape used by the module
// (_t.database.parameters was read from the server locale in Odoo 15)
try {
    if (!_t.database) {
        _t.database = {
            parameters: { date_format: "yyyy-MM-dd", time_format: "HH:mm:ss" },
        };
    }
} catch (e) {
    // never mind - only used as a formatting fallback
}
const core = { qweb, _t };

// ---------------------------------------------------------------------------
// utils (was web.utils): only is_bin_size is used by the module.  A raw stored
// base64 payload starts with one of the magic characters ('/', 'R', 'i', 'P')
// or with 'data:'; anything else is treated as a reference to /web/image.
// ---------------------------------------------------------------------------
const utils = {
    is_bin_size(value) {
        if (value === false || value === undefined || value === null || value === "") {
            return false;
        }
        const s = String(value);
        return s.length > 0 && !/^[/RiPd]/.test(s);
    },
};

// ---------------------------------------------------------------------------
// ajax (was web.ajax): rpc + lazy lib loader for widget.jsLibs/cssLibs
// ---------------------------------------------------------------------------
const _loadedUrls = {};
function _loadAsset(url, isCss) {
    if (_loadedUrls[url]) {
        return _loadedUrls[url];
    }
    _loadedUrls[url] = new Promise((resolve, reject) => {
        const tag = isCss
            ? document.createElement("link")
            : document.createElement("script");
        if (isCss) {
            tag.rel = "stylesheet";
            tag.href = url;
        } else {
            tag.src = url;
        }
        tag.onload = () => resolve();
        tag.onerror = () => {
            delete _loadedUrls[url];
            reject(new Error("Failed to load " + url));
        };
        document.head.appendChild(tag);
    });
    return _loadedUrls[url];
}

const ajax = {
    rpc(params) {
        return window.__ks_orm ? window.__ks_orm.call(params.model, params.method, params.args, params.kwargs)
            : Promise.reject(new Error("ks orm bridge not ready"));
    },
    async loadLibs(widget) {
        const libs = widget.jsLibs || [];
        const cssLibs = widget.cssLibs || [];
        // JS libs MUST load strictly in the order they are declared: the
        // datalabels plugin reads the global set by Chart.js at load time, so
        // Chart.js has to be fully executed first. Dynamically-injected
        // <script> tags execute in fetch order, so loading them concurrently
        // would let the small plugin race ahead of Chart.js.
        for (const u of libs) {
            await _loadAsset(u, false);
        }
        await Promise.all(cssLibs.map((u) => _loadAsset(u, true)));
    },
};

// ---------------------------------------------------------------------------
// framework (was web.framework): blockUI / unblockUI (cosmetic, best effort)
// ---------------------------------------------------------------------------
const framework = {
    blockUI() {
        let $block = $("#o_ks_blockui_overlay");
        if (!$block.length) {
            $block = $('<div id="o_ks_blockui_overlay" style="position:fixed;inset:0;background:rgba(128,128,128,0.4);z-index:100000;display:none;"></div>');
            $("body").append($block);
        }
        $block.show();
    },
    unblockUI() {
        $("#o_ks_blockui_overlay").hide();
    },
};

// ---------------------------------------------------------------------------
// Dialog (was web.Dialog): small v17 emulation of the legacy API used here
// (new Dialog(parent, {title, size, $content, buttons}).open() and
//  Dialog.confirm(parent, message, {confirm_callback, cancel_callback}))
// ---------------------------------------------------------------------------
function _ksDialogHTML(title, bodyHtml, buttonsHtml, size) {
    const sz = size === "medium" ? "" : size === "large" ? " modal-lg" : size === "small" ? " modal-sm" : "";
    return (
        '<div class="modal fade o_ks_dialog" tabindex="-1" role="dialog">' +
        '<div class="modal-dialog' + sz + '" role="document">' +
        '<div class="modal-content">' +
        '<div class="modal-header"><h5 class="modal-title">' + title + "</h5>" +
        '<button type="button" class="btn-close o_ks_dialog_close" data-bs-dismiss="modal" aria-label="Close"></button></div>' +
        '<div class="modal-body o_ks_dialog_body">' + bodyHtml + "</div>" +
        '<div class="modal-footer">' + buttonsHtml + "</div>" +
        "</div></div></div>"
    );
}

export class Dialog {
    constructor(parent, opts) {
        this.opts = opts || {};
        this.title = this.opts.title || "";
        this.content = this.opts.$content || this.opts.content || "";
        this.buttons = this.opts.buttons || [];
        this.size = this.opts.size;
        this._modal = null;
    }

    open() {
        const self = this;
        const buttonsHtml = this.buttons
            .map((b, i) =>
                '<button type="button" class="btn ' + (b.classes || "") + '" data-i="' + i + '">' +
                (b.text || "") + "</button>"
            )
            .join("");
        const content = typeof this.content === "string" ? this.content : (this.content.prop ? this.content.prop("outerHTML") : String(this.content));
        const html = _ksDialogHTML(this.title, content || "", buttonsHtml, this.size);
        this._modal = $(html);
        $("body").append(this._modal);
        this._modal.addClass("show").css("display", "block");
        this._modal.on("click", ".o_ks_dialog_close, [data-bs-dismiss='modal']", function () {
            self.close();
        });
        this._modal.on("click", ".modal-footer .btn", function (ev) {
            const i = Number($(this).data("i"));
            const btn = self.buttons[i];
            if (btn && typeof btn.click === "function") {
                btn.click.call(self._modal[0], ev);
            }
            if (btn && btn.close) {
                self.close();
            }
        });
        this._modal.on("click", function (ev) {
            if (ev.target === this) {
                self.close();
            }
        });
        return this;
    }

    close() {
        if (this._modal) {
            this._modal.remove();
            this._modal = null;
        }
        if (this.opts && typeof this.opts.onClose === "function") {
            this.opts.onClose();
        }
    }

    static confirm(parent, message, opts) {
        const options = opts || {};
        const dlg = new Dialog(parent, {
            title: options.title || "Confirmation",
            size: "medium",
            $content: "<div>" + (message || "") + "</div>",
            buttons: [
                {
                    text: "Ok",
                    classes: "btn-primary",
                    close: true,
                    click() {
                        if (typeof options.confirm_callback === "function") {
                            options.confirm_callback();
                        }
                    },
                },
                {
                    text: "Cancel",
                    classes: "btn-secondary",
                    close: true,
                    click() {
                        if (typeof options.cancel_callback === "function") {
                            options.cancel_callback();
                        }
                    },
                },
            ],
        });
        dlg.open();
        return dlg;
    }
}

// ---------------------------------------------------------------------------
// config (was web.config): device feature detection
// ---------------------------------------------------------------------------
const config = {
    device: {
        get isMobile() {
            return window.innerWidth < 768;
        },
        get isMobileDevice() {
            return /Mobi|Android/i.test(navigator.userAgent);
        },
        // legacy numeric class: 4 (XL), 3 (LG), 2 (MD), 1 (SM), 0 (XS)
        get size_class() {
            const w = window.innerWidth;
            if (w >= 1200) return 4;
            if (w >= 992) return 3;
            if (w >= 768) return 2;
            if (w >= 576) return 1;
            return 0;
        },
    },
};

// ---------------------------------------------------------------------------
// datepicker (was web.datepicker): minimal DateWidget / DateTimeWidget that
// reproduces the exact API surface the module uses (appendTo / setValue / $input
// / on('datetime_changed') / $el), backed by a native input element.
// ---------------------------------------------------------------------------
class LegacyDateWidgetBase {
    constructor(parent) {
        this.parent = parent;
        this._handlers = {};
        this._datetime = false;
        this.$el = $(
            '<div class="o_ks_date_widget"><input type="' + this._inputType() +
            '" class="o_input form-control o_ks_date_input"/></div>'
        );
        this.$input = this.$el.find("input");
        const self = this;
        this.$input.on("change input", function () {
            self.trigger("datetime_changed", { datetime: self.$input.val() });
        });
    }

    _inputType() {
        return "datetime-local";
    }

    appendTo($target) {
        this.$el.appendTo($target);
        return Promise.resolve(this);
    }

    setValue(momentValue) {
        if (momentValue && typeof momentValue.format === "function") {
            this.$input.val(momentValue.format("YYYY-MM-DDTHH:mm:ss"));
        } else if (momentValue) {
            this.$input.val(momentValue);
        }
        this._datetime = momentValue;
        return this;
    }

    getValue() {
        return this.$input.val();
    }

    on(eventName, obj, cb) {
        if (typeof obj === "function") {
            cb = obj;
        }
        (this._handlers[eventName] = this._handlers[eventName] || []).push(cb);
        return this;
    }

    trigger(eventName, payload) {
        (this._handlers[eventName] || []).forEach((cb) => {
            try {
                cb.call(this, payload);
            } catch (e) {
                console.error("ks datepicker handler error", e);
            }
        });
        this.$el.trigger(eventName, payload);
        return this;
    }

    destroy() {
        this.$el.remove();
    }
}

export const datepicker = {
    DateWidget: class extends LegacyDateWidgetBase {
        _inputType() {
            return "date";
        }
    },
    DateTimeWidget: class extends LegacyDateWidgetBase {},
};
// .include() patches (ks_date_picker.js) must be able to hook the widgets
_makeExtendable(datepicker.DateWidget);
_makeExtendable(datepicker.DateTimeWidget);

// ---------------------------------------------------------------------------
// searchUtils (was web.searchUtils): FIELD_TYPES / FIELD_OPERATORS used by the
// custom domain filter UI.  Represents the Odoo 15 selection faithfully for the
// field types the module renders.
// ---------------------------------------------------------------------------
const FIELD_OPERATORS = {
    char: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
        { symbol: "like", value: "like", text: "contains" },
        { symbol: "not like", value: "not like", text: "does not contain" },
        { symbol: "ilike", value: "ilike", text: "contains (case insensitive)" },
        { symbol: "not ilike", value: "not ilike", text: "does not contain (case insensitive)" },
        { symbol: "=like", value: "=like", text: "matches" },
        { symbol: "set", value: "set", text: "is set" },
        { symbol: "not set", value: "not set", text: "is not set" },
    ],
    number: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
        { symbol: ">", value: ">", text: "is greater than" },
        { symbol: ">=", value: ">=", text: "is greater than or equal to" },
        { symbol: "<", value: "<", text: "is less than" },
        { symbol: "<=", value: "<=", text: "is less than or equal to" },
        { symbol: "set", value: "set", text: "is set" },
        { symbol: "not set", value: "not set", text: "is not set" },
    ],
    date: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
        { symbol: ">", value: ">", text: "is after" },
        { symbol: ">=", value: ">=", text: "is after or equal to" },
        { symbol: "<", value: "<", text: "is before" },
        { symbol: "<=", value: "<=", text: "is before or equal to" },
        { symbol: "between", value: "between", text: "is between" },
        { symbol: "set", value: "set", text: "is set" },
        { symbol: "not set", value: "not set", text: "is not set" },
    ],
    datetime: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
        { symbol: ">", value: ">", text: "is after" },
        { symbol: ">=", value: ">=", text: "is after or equal to" },
        { symbol: "<", value: "<", text: "is before" },
        { symbol: "<=", value: "<=", text: "is before or equal to" },
        { symbol: "between", value: "between", text: "is between" },
        { symbol: "set", value: "set", text: "is set" },
        { symbol: "not set", value: "not set", text: "is not set" },
    ],
    selection: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
        { symbol: "set", value: "set", text: "is set" },
        { symbol: "not set", value: "not set", text: "is not set" },
    ],
    boolean: [
        { symbol: "=", value: "=", text: "is" },
        { symbol: "!=", value: "!=", text: "is not" },
    ],
    id: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
    ],
    relational: [
        { symbol: "=", value: "=", text: "is equal to" },
        { symbol: "!=", value: "!=", text: "is not equal to" },
        { symbol: "in", value: "in", text: "is in" },
        { symbol: "not in", value: "not in", text: "is not in" },
        { symbol: "set", value: "set", text: "is set" },
        { symbol: "not set", value: "not set", text: "is not set" },
    ],
};

const FIELD_TYPES = {
    char: "char",
    text: "char",
    html: "char",
    selection: "selection",
    boolean: "boolean",
    date: "date",
    datetime: "datetime",
    integer: "number",
    float: "number",
    monetary: "number",
    many2one: "relational",
    one2many: "relational",
    many2many: "relational",
    id: "id",
};

// ---------------------------------------------------------------------------
// include() targets whose Odoo 15 host classes were deleted in Odoo 17.
// The code of the original patches is preserved (see ks_domain_fix.js /
// ks_import_dashboard.js) but the hosts no longer exist in the web client, so
// the patches are inert.  Documented per-file.
// ---------------------------------------------------------------------------
class _InertLegacyTarget {}
_makeExtendable(_InertLegacyTarget);
const BasicModel = _InertLegacyTarget;
const ListController = _InertLegacyTarget;
const BasicFields = { FieldDomain: _InertLegacyTarget };

// ---------------------------------------------------------------------------
// LegacyAbstractAction - base of the (extend-style) dashboard action.
// The OWL host component instantiates it and bridges env services.
// ---------------------------------------------------------------------------
export class LegacyAbstractAction {
    constructor() {
        this._ksHost = null;
        this.state = {};
        this.env = null;
    }

    // bridge used by host / services
    _getHost() {
        return this._ksHost;
    }

    // -- legacy Widget / ServiceMixin conveniences used by the module -------
    get $el() {
        return this._ksHost ? $(this._ksHost) : $();
    }

    getParent() {
        return {
            actionService: (this.env && this.env.services && this.env.services.action) || {},
        };
    }

    getSession() {
        return ksSession;
    }

    _rpc(params) {
        const orm = this.env && this.env.services && this.env.services.orm;
        if (!orm) {
            return Promise.reject(new Error("ks: orm service not available"));
        }
        // v17 orm.call(model, method, args, kwargs, context) - keep the legacy
        // `context` key the module passes (user context / date filters), like
        // the v15 ajax.rpc did.
        return orm.call(
            params.model,
            params.method,
            params.args,
            params.kwargs || {},
            params.context || {}
        );
    }

    do_action(action, options) {
        const actionService = this.env && this.env.services && this.env.services.action;
        if (!actionService) {
            return Promise.reject(new Error("ks: action service not available"));
        }
        return actionService.doAction(action, options || {});
    }

    trigger_up() {
        // legacy event bubbling - handled by the host where relevant
    }

    call(serviceName, method) {
        const service = this.env && this.env.services && this.env.services[serviceName];
        const fn = service && typeof service[method] === "function" ? service[method] : null;
        if (fn) {
            const args = Array.prototype.slice.call(arguments, 2);
            return fn.apply(service, args);
        }
        console.error("ks: cannot call service", serviceName, method);
        return null;
    }

    // -- lifecycle hooks (defaults; overridden by the subclass) -------------
    willStart() {
        return Promise.resolve();
    }
    start() {
        return Promise.resolve();
    }
    on_attach_callback() {
        return Promise.resolve();
    }
    on_detach_callback() {}

    // -- event delegation ----------------------------------------------------
    // Odoo 15's widget framework bound `this.events` to the action root
    // automatically; the Odoo 17 host has no such machinery, so the events
    // are bound here (jQuery delegated) as soon as the action is mounted.
    _bindEvents() {
        if (this._eventsBound) {
            return;
        }
        this._eventsBound = true;
        const events = this.events || {};
        for (const key of Object.keys(events)) {
            const idx = key.indexOf(" ");
            const eventName = idx === -1 ? key : key.slice(0, idx);
            const selector = idx === -1 ? undefined : key.slice(idx + 1);
            const handler = events[key];
            if (typeof handler === "function") {
                this.$el.on(eventName, selector, handler.bind(this));
            } else if (typeof this[handler] === "function") {
                this.$el.on(eventName, selector, (ev) => this[handler](ev));
            }
        }
    }

    _unbindEvents() {
        if (this._eventsBound) {
            this.$el.off();
            this._eventsBound = false;
        }
    }
}
_makeExtendable(LegacyAbstractAction);

// ---------------------------------------------------------------------------
// OWL host for a legacy action, registered into the v17 "actions" category.
// ---------------------------------------------------------------------------
function makeActionHost(legacyClass) {
    return class extends Component {
        static template = xml`<div t-ref="root" class="ks_dn_action_host"/>`;
        static props = { action: Object };
        setup() {
            this.rootRef = useRef("root");
            this.legacy = new legacyClass();
            this.legacy.env = this.env;
            this.legacy.actionService = this.env.services.action;
            onMounted(() => this._boot());
            // First-open safety net: when a dashboard is opened directly after
            // login the OWL action sometimes mounts before the legacy widget
            // produced any content (blank screen).  Reload the page ONCE per
            // session so the dashboard renders; afterwards it opens instantly.
            window.setTimeout(() => {
                try {
                    const host = this.rootRef.el;
                    const finished = window.__ksBootStep === "done" || window.__ksBootError;
                    if (!host) return;
                    if (host.children.length > 0) {
                        // content rendered: allow a future retry if needed
                        sessionStorage.removeItem("ks_dn_auto_reload");
                    } else if (finished) {
                        // blank screen: reload the page once so the dashboard
                        // renders (same as the manual refresh the user needed)
                        if (!sessionStorage.getItem("ks_dn_auto_reload")) {
                            sessionStorage.setItem("ks_dn_auto_reload", "1");
                            window.location.reload();
                        }
                    }
                } catch (e) {
                    /* never mind */
                }
            }, 1800);
            onWillUnmount(() => {
                try {
                    if (this.legacy && typeof this.legacy.on_detach_callback === "function") {
                        this.legacy.on_detach_callback();
                    }
                    if (this.legacy && typeof this.legacy._unbindEvents === "function") {
                        this.legacy._unbindEvents();
                    }
                } catch (e) {
                    console.error("ks action detach error", e);
                }
                $(document).off("click.ks_dn_outside");
            });
        }

        async _boot() {
            const legacy = this.legacy;
            const action = this.props.action || {};
            legacy._ksHost = this.rootRef.el;
            // mount our container element the way the legacy widget expected it
            const state = {
                context: action.context || {},
                params: action.params || {},
            };
            legacy.state = state;
            const mark = (step) => { window.__ksBootStep = step; };
            try {
                mark("init");
                if (typeof legacy.init === "function") {
                    legacy.init(undefined, state, { controllerID: undefined });
                }
                if (typeof legacy._bindEvents === "function") {
                    legacy._bindEvents();
                }
                mark("willStart");
                await legacy.willStart();
                mark("start");
                await legacy.start();
                mark("attach");
                if (typeof legacy.on_attach_callback === "function") {
                    await legacy.on_attach_callback();
                }
                mark("done");
            } catch (e) {
                window.__ksBootError = String((e && e.stack) || e);
                console.error("ks_dashboard_ninja action boot error", e);
            }
        }
    };
}

// core.action_registry -> v17 actions registry (client action with tag
// "ks_dashboard_ninja" is looked up there by the ActionService)
core.action_registry = {
    add(name, legacyClass) {
        registry.category("actions").add(name, makeActionHost(legacyClass));
    },
};

// orm bridge used by ajax.rpc (set by the first mounted action host)
export function setOrmBridge(orm) {
    window.__ks_orm = orm;
}

// Safely resolve the display name of a record's model m2o. In Odoo >=16 the
// record data m2o is a plain [id, display_name] tuple, in 15 it was an object
// with a .data attr — never assume one shape (widgets crash on unsaved items).
export function ksModelDisplayName(field) {
    if (!field) return '';
    if (field.name) return field.name;
    const m = field.ks_model_id;
    if (m) {
        if (m.data && m.data.display_name) return m.data.display_name;
        if (Array.isArray(m)) return m[1] || m[0] || '';
        if (m.display_name) return m.display_name;
    }
    return field.ks_model_name || '';
}

// ---------------------------------------------------------------------------
// generic exports consumed by the transformed files
// ---------------------------------------------------------------------------
export {
    registry,
    standardFieldProps,
    qweb,
    core,
    field_utils,
    time,
    config,
    framework,
    ajax,
    datepicker,
    Dialog,
    fieldRegistry,
    ksModelDisplayName,
    ksSession,
    _t,
    session,
    FIELD_TYPES,
    FIELD_OPERATORS,
    utils,
    BasicModel,
    BasicFields,
    ListController,
};
