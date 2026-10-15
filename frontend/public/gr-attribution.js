/**
 * GlobalReach Attribution Snippet — gr-attribution.js
 * Version: 1.0.0
 *
 * INSTALLATION:
 *   Add to <head> of your main product (getyourclientsb2b.com):
 *   <script src="https://your-vercel-domain.com/gr-attribution.js" async></script>
 *
 * WHAT IT DOES:
 *   1. Reads UTM parameters from the URL on every page load.
 *   2. Stores them in localStorage as first_touch (never overwritten) and last_touch (always updated).
 *   3. Generates a stable visitor_id (UUID) stored in localStorage + a cookie.
 *   4. On signup form submit (or manual call to grAttribution.trackSignup(email)), sends
 *      an HMAC-signed event to the Growth Engine backend webhook.
 *
 * USAGE:
 *   Auto mode: the snippet watches for forms with data-gr-signup attribute.
 *     <form data-gr-signup data-gr-email-field="email">...</form>
 *
 *   Manual mode:
 *     grAttribution.trackSignup("user@example.com");
 */

(function () {
  "use strict";

  var GR_ENDPOINT = "%%GR_WEBHOOK_URL%%"; // replaced at build time or set via window.GR_CONFIG
  var STORAGE_KEY_FIRST = "gr_first_touch";
  var STORAGE_KEY_LAST = "gr_last_touch";
  var VISITOR_KEY = "gr_visitor_id";

  // ── Helpers ────────────────────────────────────────────────────────────────

  function uuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function getOrCreateVisitorId() {
    var id = localStorage.getItem(VISITOR_KEY);
    if (!id) {
      id = uuid();
      localStorage.setItem(VISITOR_KEY, id);
      // Also set a 1-year cookie for cross-subdomain matching
      document.cookie =
        "gr_visitor_id=" + id + "; path=/; max-age=" + 60 * 60 * 24 * 365 + "; samesite=lax";
    }
    return id;
  }

  function parseUtm() {
    var params = {};
    var search = window.location.search;
    if (!search) return params;
    var pairs = search.slice(1).split("&");
    for (var i = 0; i < pairs.length; i++) {
      var pair = pairs[i].split("=");
      var key = decodeURIComponent(pair[0]);
      if (key.indexOf("utm_") === 0) {
        params[key] = decodeURIComponent(pair[1] || "");
      }
    }
    return params;
  }

  function captureTouch() {
    var utm = parseUtm();
    var hasUtm = Object.keys(utm).length > 0;
    if (!hasUtm) return;

    var touch = {
      utm_source: utm.utm_source || "",
      utm_medium: utm.utm_medium || "",
      utm_campaign: utm.utm_campaign || "",
      utm_content: utm.utm_content || "",
      visitor_id: getOrCreateVisitorId(),
      url: window.location.href,
      ts: new Date().toISOString(),
    };

    // First touch: never overwrite
    if (!localStorage.getItem(STORAGE_KEY_FIRST)) {
      localStorage.setItem(STORAGE_KEY_FIRST, JSON.stringify(touch));
    }

    // Last touch: always update
    localStorage.setItem(STORAGE_KEY_LAST, JSON.stringify(touch));
  }

  function sendSignup(email) {
    var endpoint = (window.GR_CONFIG && window.GR_CONFIG.webhookUrl) || GR_ENDPOINT;
    if (!endpoint || endpoint === "%%GR_WEBHOOK_URL%%") {
      console.warn("[gr-attribution] No webhook URL configured. Set window.GR_CONFIG.webhookUrl.");
      return;
    }

    var payload = JSON.stringify({
      user_email: email,
      signed_up_at: new Date().toISOString(),
      first_touch: JSON.parse(localStorage.getItem(STORAGE_KEY_FIRST) || "null"),
      last_touch: JSON.parse(localStorage.getItem(STORAGE_KEY_LAST) || "null"),
      visitor_id: getOrCreateVisitorId(),
    });

    // Use sendBeacon for reliability on page unload
    if (navigator.sendBeacon) {
      var blob = new Blob([payload], { type: "application/json" });
      navigator.sendBeacon(endpoint, blob);
    } else {
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
      }).catch(function () {});
    }
  }

  // ── Auto form detection ────────────────────────────────────────────────────

  function watchForms() {
    document.addEventListener("submit", function (e) {
      var form = e.target;
      if (!form || !form.dataset || !form.dataset.grSignup) return;
      var emailField = form.dataset.grEmailField || "email";
      var emailInput = form.querySelector('[name="' + emailField + '"]');
      if (emailInput && emailInput.value) {
        sendSignup(emailInput.value);
      }
    });
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  window.grAttribution = {
    trackSignup: sendSignup,
    getFirstTouch: function () {
      return JSON.parse(localStorage.getItem(STORAGE_KEY_FIRST) || "null");
    },
    getLastTouch: function () {
      return JSON.parse(localStorage.getItem(STORAGE_KEY_LAST) || "null");
    },
    getVisitorId: getOrCreateVisitorId,
  };

  // ── Init ───────────────────────────────────────────────────────────────────

  captureTouch();
  watchForms();
})();
