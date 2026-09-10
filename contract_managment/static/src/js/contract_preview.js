(function () {
    "use strict";

    function getEditor() {
        return document.querySelector(
            ".cp-editor-area .odoo-editor-editable, .cp-editor-area .o_editable"
        );
    }

    function exec(cmd, val) {
        var ed = getEditor();
        if (ed) { ed.focus(); }
        document.execCommand(cmd, false, val || null);
    }

    function wireToolbar() {
        var toolbar = document.getElementById("cp_toolbar");
        if (!toolbar || toolbar._wired) return;
        toolbar._wired = true;

        /* ── command buttons ── */
        toolbar.querySelectorAll("button[data-cmd]").forEach(function (btn) {
            btn.addEventListener("mousedown", function (e) {
                e.preventDefault();
                exec(btn.dataset.cmd, btn.dataset.val || null);
            });
        });

        /* ── font family ── */
        var fontSel = document.getElementById("cp_font");
        if (fontSel) {
            fontSel.addEventListener("change", function () {
                exec("fontName", fontSel.value);
            });
        }

        /* ── font size ── */
        var sizeSel = document.getElementById("cp_size");
        if (sizeSel) {
            sizeSel.addEventListener("change", function () {
                var ed = getEditor();
                if (!ed) return;
                ed.focus();
                /* execCommand fontSize only accepts 1-7; use a wrapper span instead */
                document.execCommand("fontSize", false, "7");
                ed.querySelectorAll("font[size='7']").forEach(function (node) {
                    node.removeAttribute("size");
                    node.style.fontSize = sizeSel.value + "pt";
                });
            });
        }

        /* ── text color ── */
        var colorPick = document.getElementById("cp_color_pick");
        if (colorPick) {
            colorPick.addEventListener("input", function () {
                exec("foreColor", colorPick.value);
            });
        }

        /* ── active state on selectionchange ── */
        document.addEventListener("selectionchange", function () {
            toolbar.querySelectorAll("button[data-cmd]").forEach(function (btn) {
                var cmd = btn.dataset.cmd;
                if (["bold","italic","underline","strikeThrough",
                     "justifyLeft","justifyCenter","justifyRight","justifyFull",
                     "insertUnorderedList","insertOrderedList"].indexOf(cmd) !== -1) {
                    try {
                        btn.classList.toggle("cp-active", document.queryCommandState(cmd));
                    } catch(e) {}
                }
            });
        });
    }

    /* watch for the toolbar + editor to appear in the DOM */
    var obs = new MutationObserver(function () {
        if (document.getElementById("cp_toolbar") && getEditor()) {
            wireToolbar();
        }
    });
    obs.observe(document.body, { childList: true, subtree: true });

    /* fallback */
    setTimeout(wireToolbar, 800);
    setTimeout(wireToolbar, 1800);
})();
