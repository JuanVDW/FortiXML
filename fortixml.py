import re
from pathlib import Path

import streamlit as st
from jinja2 import Template

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="FortiXML", page_icon="logo.png", layout="centered")

TEMPLATE_PATH = Path("template.xml")

# ----------------------------
# Helpers
# ----------------------------
def extract_template_vars(template_text: str) -> set[str]:
    return set(re.findall(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}", template_text))

def yn_to_01(value: bool) -> int:
    return 1 if value else 0

def validate(values: dict) -> list[str]:
    issues = []
    if not values["var_name"].strip():
        issues.append("Name is empty.")
    if not values["var_server"].strip():
        issues.append("Server is empty.")
    port = int(values["var_ike_saml_port"])
    if not (0 <= port <= 65535):
        issues.append("IKE SAML port must be between 1 and 65535.")
    if int(values["var_networkid"]) < 0:
        issues.append("NetworkID should be >= 0.")
    if not values["var_preshared_key"]:
        issues.append("Preshared key is empty (XML will still be generated).")
    return issues

# ----------------------------
# Header
# ----------------------------
col1, col2 = st.columns([1, 5])
with col1:
    st.image("logo.png", width=120)
with col2:
    st.markdown(
        "<h1 style='margin-top: 7px;margin-left:-20px;'>FortiClient XML generator</h1>",
        unsafe_allow_html=True
    )

# ----------------------------
# Load template
# ----------------------------
if not TEMPLATE_PATH.exists():
    st.error("template.xml not found next to the app.")
    st.stop()

template_text = TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
template = Template(template_text)
_ = extract_template_vars(template_text)  # optional: keep if you want later checks

# ----------------------------
# Defaults
# ----------------------------
DEFAULTS = {
    "var_name": "Acme - IT grp",
    "var_description": "IPSec VPN for Acme IT grp",
    "var_server": "acme.vpn.com",
    "var_preshared_key": "",
    "var_sso_enabled": 0,
    "var_ike_saml_port": 443,
    "var_use_external_browser": 0,
    "var_networkid": 10,
    "var_transport_mode": 2,
    "var_enable_local_lan": 0,
}

TRANSPORT_LABEL_TO_VALUE = {
    "UDP only": 0,
    "TCP only": 1,
    "Auto": 2
}

# ----------------------------
# Initialize session state once
# ----------------------------
def init_state():
    st.session_state.setdefault("var_name", DEFAULTS["var_name"])
    st.session_state.setdefault("var_description", DEFAULTS["var_description"])
    st.session_state.setdefault("var_server", DEFAULTS["var_server"])
    st.session_state.setdefault("var_sso_enabled_bool", False)
    st.session_state.setdefault("auth_key", "saml")
    st.session_state.setdefault("use_external_browser", bool(DEFAULTS["var_use_external_browser"]))
    st.session_state.setdefault("ike_saml_port", int(DEFAULTS["var_ike_saml_port"]))
    st.session_state.setdefault("var_preshared_key", DEFAULTS["var_preshared_key"])
    st.session_state.setdefault("var_networkid", int(DEFAULTS["var_networkid"]))
    st.session_state.setdefault("var_transport_mode_label", "Auto")

init_state()

# ----------------------------
# UI (NO st.form) + Tabs
# ----------------------------
tab_general, tab_auth, tab_ipsec = st.tabs(["General", "Authentication", "IPSec"])

with tab_general:
    st.text_input("Name", key="var_name")
    st.text_area("Description", key="var_description")
    st.text_input("Server (FQDN/IP)", key="var_server")
    st.toggle(
        "Enable local LAN",
        key="var_enable_local_lan_bool",
        help="Only in case of full tunneling (and if needed)",
    )

with tab_auth:
    st.toggle(
        "SSO enabled", 
        key="var_sso_enabled_bool",
        help="If authentication via SAML is used",
    )

    is_saml = bool(st.session_state["var_sso_enabled_bool"])

    if is_saml and int(st.session_state.get("ike_saml_port", 0)) == 0:
        st.session_state["ike_saml_port"] = 443

    if is_saml:
        c1, c2 = st.columns(2)
        with c1:
            st.toggle("Use external browser", key="use_external_browser")
        with c2:
            st.number_input(
                "IKE SAML port",
                min_value=0,
                max_value=65535,
                step=1,
                key="ike_saml_port",
                help="Default: 443"
            )
    else:
        st.session_state["use_external_browser"] = False
        st.session_state["ike_saml_port"] = 0

with tab_ipsec:
    st.text_input("Preshared key", type="password", key="var_preshared_key")
    st.number_input(
        "NetworkID",
        min_value=0,
        max_value=255,
        step=1,   
        key="var_networkid"
    ) 
    st.selectbox(
        "Transport mode",
        ["Auto", "UDP only", "TCP only"],
        key="var_transport_mode_label",
        help="UDP only, TCP only, or Auto: UDP with TCP fallback",
    )

# ----------------------------
# Render button (outside tabs)
# ----------------------------
render_clicked = st.button("✅ Render XML", type="primary", use_container_width=True)

# ----------------------------
# Build values + Render + Download
# ----------------------------
if render_clicked:
    auth_key = st.session_state["auth_key"]
    is_saml = bool(st.session_state["var_sso_enabled_bool"])

    networkid_int = int(st.session_state["var_networkid"])

    var_use_external_browser_bool = bool(st.session_state["use_external_browser"]) if is_saml else False
   
    var_ike_saml_port = int(st.session_state["ike_saml_port"]) if is_saml else 0

    values = {
        "var_name": st.session_state["var_name"],
        "var_description": st.session_state["var_description"],
        "var_server": st.session_state["var_server"],
        "var_preshared_key": st.session_state["var_preshared_key"],
        "var_networkid": networkid_int,
        "var_transport_mode": TRANSPORT_LABEL_TO_VALUE.get(st.session_state["var_transport_mode_label"], 2),
        "var_enable_local_lan": yn_to_01(bool(st.session_state["var_enable_local_lan_bool"])),
        "var_sso_enabled": yn_to_01(is_saml),
        "var_use_external_browser": yn_to_01(var_use_external_browser_bool),
        "var_ike_saml_port": var_ike_saml_port,
    }

    issues = validate(values)
    if issues:
        st.warning("Some checks raised warnings:")
        for i in issues:
            st.write(f"- {i}")
    else:
        st.success("All checks look good.")

    rendered_xml = template.render(**values)

    invalid_chars = '<>:"/\\|?*'
    safe_name = "".join(c for c in st.session_state["var_name"].strip() if c not in invalid_chars)
    filename = f"{safe_name}.xml" if safe_name else "config.xml"

    # --- Make download button red ---
    st.markdown("""
    <style>
    div[data-testid="stDownloadButton"] > button {
        background-color: #ff4b4b;
        color: white;
        border: none;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #ff2b2b;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.download_button(
        "⬇️ Download XML",
        rendered_xml.encode("utf-8"),
        file_name=filename,
        mime="application/xml",
        use_container_width=True,
    )

    # --- Preview inside expander ---
    with st.expander("🔎 Show XML Preview", expanded=False):
        st.code(rendered_xml, language="xml")
