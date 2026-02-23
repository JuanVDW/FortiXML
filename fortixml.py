import re
from datetime import datetime
from pathlib import Path

import streamlit as st
from jinja2 import Template

st.set_page_config(page_title="XML Generator", page_icon="🧩", layout="centered")

TEMPLATE_PATH = Path("template.xml")


def extract_template_vars(template_text: str) -> set[str]:
    # Extract {{ var_name }} occurrences (simple + robust enough for your template)
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
    if not (1 <= port <= 65535):
        issues.append("IKE SAML port must be between 1 and 65535.")
    if int(values["var_networkid"]) < 0:
        issues.append("NetworkID should be >= 0.")
    if not values["var_preshared_key"]:
        issues.append("Preshared key is empty (XML will still be generated).")
    return issues


st.title("🧩 XML configuration generator")
st.caption("Fill the fields → render XML from template.xml → download.")

if not TEMPLATE_PATH.exists():
    st.error("template.xml not found. Put template.xml next to app.py.")
    st.stop()

template_text = TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
template = Template(template_text)
template_vars = extract_template_vars(template_text)

# ---- UI defaults (from your table) ----
DEFAULTS = {
    "var_name": "Acme - IT grp",
    "var_description": "IPSec VPN for Acme IT grp",
    "var_server": "acme.vpn.com",
    "var_preshared_key": "",
    "var_sso_enabled": 1,            # yes
    "var_ike_saml_port": 443,
    "var_use_external_browser": 0,   # no
    "var_networkid": 10,
    "var_transport_mode": 2,         # Auto
    "var_enable_local_lan": 0,       # no
}

# Transport mode mapping you gave:
TRANSPORT_LABEL_TO_VALUE = {"UDP only": 0, "TCP only": 1, "Auto": 2}
TRANSPORT_VALUE_TO_LABEL = {v: k for k, v in TRANSPORT_LABEL_TO_VALUE.items()}

# ---- Form ----
with st.form("xml_form", border=True):
    tab_general, tab_sso, tab_network, tab_security = st.tabs(
        ["General", "SSO & Browser", "Network", "Security"]
    )

    with tab_general:
        var_name = st.text_input("Name", value=DEFAULTS["var_name"])
        var_description = st.text_area(
            "Description", value=DEFAULTS["var_description"], height=90
        )
        var_server = st.text_input("Server (FQDN/IP)", value=DEFAULTS["var_server"])

    with tab_sso:
        c1, c2 = st.columns(2)
        with c1:
            sso_enabled_bool = st.toggle(
                "SSO enabled",
                value=bool(DEFAULTS["var_sso_enabled"]),
                help="Stored as 1 (yes) / 0 (no)",
            )
        with c2:
            external_browser_bool = st.toggle(
                "Use external browser",
                value=bool(DEFAULTS["var_use_external_browser"]),
                help="Stored as 1 (yes) / 0 (no)",
            )

        var_ike_saml_port = st.number_input(
            "IKE SAML Port",
            min_value=1,
            max_value=65535,
            value=int(DEFAULTS["var_ike_saml_port"]),
            step=1,
        )

    with tab_network:
        c1, c2 = st.columns(2)
        with c1:
            var_networkid = st.number_input(
                "NetworkID", min_value=0, value=int(DEFAULTS["var_networkid"]), step=1
            )
        with c2:
            local_lan_bool = st.toggle(
                "Enable local LAN",
                value=bool(DEFAULTS["var_enable_local_lan"]),
                help="Stored as 1 (yes) / 0 (no)",
            )

        transport_default_label = TRANSPORT_VALUE_TO_LABEL.get(
            int(DEFAULTS["var_transport_mode"]), "Auto"
        )
        var_transport_mode_label = st.selectbox(
            "Transport mode",
            ["Auto", "UDP only", "TCP only"],
            index=["Auto", "UDP only", "TCP only"].index(transport_default_label),
            help="UDP only: 0, TCP only: 1, Auto: 2 (default)",
        )

    with tab_security:
        var_preshared_key = st.text_input(
            "Preshared key",
            value=DEFAULTS["var_preshared_key"],
            type="password",
        )

    submitted = st.form_submit_button("✅ Render XML", type="primary", use_container_width=True)

# ---- Build values dict ----
values = {
    "var_name": var_name,
    "var_description": var_description,
    "var_server": var_server,
    "var_preshared_key": var_preshared_key,
    "var_sso_enabled": yn_to_01(sso_enabled_bool),
    "var_ike_saml_port": int(var_ike_saml_port),
    "var_use_external_browser": yn_to_01(external_browser_bool),
    "var_networkid": int(var_networkid),
    "var_transport_mode": TRANSPORT_LABEL_TO_VALUE[var_transport_mode_label],
    "var_enable_local_lan": yn_to_01(local_lan_bool),
}

# ---- Template/form consistency checks ----
form_vars = set(values.keys())
missing_in_form = sorted(template_vars - form_vars)
unused_in_template = sorted(form_vars - template_vars)

with st.expander("🔎 Template variable check", expanded=False):
    st.write("Variables found in template.xml:", sorted(template_vars))
    if missing_in_form:
        st.error(f"Template variables missing in the form: {missing_in_form}")
    else:
        st.success("All template variables are covered by the form ✅")

    if unused_in_template:
        st.warning(f"Form variables not used in template.xml: {unused_in_template}")

# ---- Render + Download ----
if submitted:
    issues = validate(values)
    if issues:
        st.warning("Some checks raised warnings:")
        for i in issues:
            st.write(f"- {i}")
    else:
        st.success("All checks look good.")

    rendered_xml = template.render(**values)

    st.subheader("Preview")
    st.code(rendered_xml, language="xml")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in var_name.strip())
    filename = f"{safe_name or 'config'}_{ts}.xml"

    st.download_button(
        label="⬇️ Download XML",
        data=rendered_xml.encode("utf-8"),
        file_name=filename,
        mime="application/xml",
        use_container_width=True,
    )
