
import streamlit as st
import pandas as pd
import unicodedata
from html import escape

from ai_service import extract_enquiry, generate_reply

from database import (
    get_all_enquiries,
    save_enquiry,
    update_enquiry_status,
    update_enquiry,
    delete_enquiry,
    matching_enquiries
)


# ----------------------------------------
# APP CONFIGURATION
# ----------------------------------------

st.set_page_config(
    page_title="BIAI SmartCRM",
    page_icon="✦",
    layout="wide"
)

SOURCES = [
    "Unknown",
    "WhatsApp",
    "Facebook",
    "Website",
    "Phone Call"
]

PROGRAMMES = [
    "Unknown",
    "Bootcamp",
    "Fellowship",
    "Corporate Training"
]

STATUSES = [
    "New",
    "Contacted",
    "Interested",
    "Paid",
    "Lost"
]


# ----------------------------------------
# CUSTOM STYLING
# ----------------------------------------

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    max-width: 1250px;
}

/* Dashboard metrics */

[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #DED7CC !important;
    border-top: 4px solid #D45116 !important;
    padding: 18px 20px !important;
    border-radius: 16px !important;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: #55504A !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    color: #161616 !important;
}

/* Saved enquiry expanders */

[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid #DED7CC;
    border-radius: 14px;
    margin-bottom: 12px;
    overflow: hidden;
}

[data-testid="stExpander"] summary {
    font-weight: 600;
}

/* Hide heading link icons */

[data-testid="stHeading"] a {
    visibility: hidden;
}

/* Hide unnecessary chart toolbar */

[data-testid="stElementToolbar"] {
    display: none !important;
}

/* Tracker card information */

.tracker-name {
    color: #111111;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.3;
    margin-bottom: 12px;
    overflow-wrap: anywhere;
}

.tracker-detail {
    color: #55504A;
    font-size: 12px;
    line-height: 1.5;
    margin: 4px 0;
    white-space: nowrap;
}

</style>
""", unsafe_allow_html=True)


# ----------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------

st.sidebar.title("BIAI SmartCRM")
st.sidebar.caption("AI-powered enquiry management")
st.sidebar.divider()

page = st.sidebar.radio(
    "Pages",
    [
        "Dashboard",
        "AI Enquiry Assistant",
        "Enquiries",
        "Enquiry Tracker"
    ],
    label_visibility="collapsed"
)


# ----------------------------------------
# SESSION STATE
# ----------------------------------------

initial_state = {
    "extracted_data": None,
    "suggested_reply": "",
    "last_message": "",
    "saved_enquiry_id": None,
    "processed_message": ""
}

for key, value in initial_state.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ----------------------------------------
# SEARCH FUNCTIONS
# ----------------------------------------

def normalize_search_text(value):
    """Normalize text for case-insensitive searches."""

    text = unicodedata.normalize(
        "NFKC",
        str(value or "")
    )

    return " ".join(text.casefold().split())


def matches_search(enquiry, query):
    """Search all important enquiry fields."""

    if not query.strip():
        return True

    searchable_fields = [
        "id",
        "name",
        "phone",
        "source",
        "programme",
        "status",
        "language",
        "message",
        "suggested_reply",
        "created_at"
    ]

    combined_text = " ".join(
        str(enquiry.get(field) or "")
        for field in searchable_fields
    )

    combined_text = normalize_search_text(
        combined_text
    )

    search_words = normalize_search_text(
        query
    ).split()

    return all(
        word in combined_text
        for word in search_words
    )


# Load saved enquiries
records = get_all_enquiries()


# ========================================
# DASHBOARD
# ========================================

if page == "Dashboard":

    st.title("Dashboard")
    total = len(records)
    new_count = sum(
        enquiry["status"] == "New"
        for enquiry in records
    )

    interested_count = sum(
        enquiry["status"] == "Interested"
        for enquiry in records
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Enquiries", total)
    col2.metric("New", new_count)
    col3.metric("Interested", interested_count)

    st.subheader("Pipeline Overview")

    stage_counts = {
        status: sum(
            enquiry["status"] == status
            for enquiry in records
        )
        for status in STATUSES
    }

    chart_data = pd.DataFrame(
        {
            "Enquiries": list(stage_counts.values())
        },
        index=list(stage_counts.keys())
    )

    st.bar_chart(
        chart_data,
        color="#D45116"
    )


# ========================================
# AI ENQUIRY ASSISTANT
# ========================================

elif page == "AI Enquiry Assistant":

    st.title("AI Enquiry Assistant")

    message = st.text_area(
        "Paste Customer Enquiry",
        value=st.session_state.last_message,
        height=180,
        placeholder="",
        key="message_input"
    )

    if st.button(
        "Extract Information with AI",
        type="primary"
    ):

        if not message.strip():
            st.warning("Please paste an enquiry first.")

        else:
            fields_to_clear = [
                "customer_name",
                "customer_phone",
                "customer_source",
                "customer_programme",
                "customer_status",
                "customer_language",
                "reply_editor"
            ]

            for field in fields_to_clear:
                st.session_state.pop(field, None)

            st.session_state.extracted_data = None
            st.session_state.suggested_reply = ""
            st.session_state.saved_enquiry_id = None
            st.session_state.last_message = message

            try:
                with st.spinner("Extracting information..."):
                    result = extract_enquiry(message)

                st.session_state.extracted_data = result
                st.session_state.processed_message = message

                try:
                    with st.spinner("Generating suggested reply..."):
                        reply = generate_reply(
                            message,
                            result.get("language") or "English",
                            result.get("name")
                        )

                    st.session_state.suggested_reply = reply

                except Exception as error:
                    st.warning(
                        f"Reply generation unavailable: {error}"
                    )

            except Exception as error:
                st.error(
                    f"AI extraction failed: {error}"
                )

    result = st.session_state.extracted_data

    if result is not None:

        st.success("Information extracted successfully!")

        initial_fields = {
            "customer_name": result.get("name") or "",
            "customer_phone": result.get("phone") or "",
            "customer_source": result.get("source") or "Unknown",
            "customer_programme": result.get("programme") or "Unknown",
            "customer_status": "New",
            "customer_language": result.get("language") or "English",
            "reply_editor": st.session_state.suggested_reply
        }

        for field, value in initial_fields.items():
            if field not in st.session_state:
                st.session_state[field] = value

        st.subheader("Extracted Customer Information")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Customer Name",
                key="customer_name"
            )

            st.text_input(
                "Phone Number",
                key="customer_phone"
            )

            st.selectbox(
                "Enquiry Source",
                SOURCES,
                key="customer_source"
            )

        with col2:
            st.selectbox(
                "Interested Programme",
                PROGRAMMES,
                key="customer_programme"
            )

            st.selectbox(
                "Enquiry Status",
                STATUSES,
                key="customer_status"
            )

            st.text_input(
                "Detected Language",
                key="customer_language"
            )

        st.divider()
        st.subheader("AI Suggested Reply")

        st.caption(
            "Review and edit this draft before sending."
        )

        st.text_area(
            "Suggested Reply",
            height=140,
            key="reply_editor"
        )

        st.divider()
        st.subheader("Save Enquiry")

        # Check duplicate enquiries only before saving
        if st.session_state.saved_enquiry_id is None:

            duplicates = matching_enquiries(
                st.session_state.customer_phone,
                st.session_state.processed_message
            )

            if duplicates:

                ids = ", ".join(
                    str(item["id"])
                    for item in duplicates
                )

                st.warning(
                    f"Possible duplicate enquiry. "
                    f"Existing ID(s): {ids}"
                )

        if st.session_state.saved_enquiry_id is not None:

            st.success("Enquiry saved successfully!")

        else:

            if st.button(
                "Save Enquiry",
                type="primary"
            ):

                try:
                    enquiry_id = save_enquiry(
                        st.session_state.customer_name,
                        st.session_state.customer_phone,
                        st.session_state.customer_source,
                        st.session_state.customer_programme,
                        st.session_state.customer_status,
                        st.session_state.customer_language,
                        st.session_state.processed_message,
                        st.session_state.reply_editor
                    )

                    st.session_state.saved_enquiry_id = enquiry_id
                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Could not save enquiry: {error}"
                    )


# ========================================
# SAVED ENQUIRIES
# ========================================

elif page == "Enquiries":

    st.title("Saved Enquiries")

    if not records:
        st.info("No enquiries saved yet.")

    else:
        st.metric(
            "Total Saved Enquiries",
            len(records)
        )

        query = st.text_input(
            "Search Enquiries",
            placeholder=(
                "Name, phone, programme, source, "
                "status, message..."
            )
        )

        filtered_records = [
            enquiry
            for enquiry in records
            if matches_search(enquiry, query)
        ]

        st.caption(
            f"Showing {len(filtered_records)} "
            f"of {len(records)} enquiries"
        )

        if not filtered_records:
            st.info("No matching enquiries found.")

        for enquiry in filtered_records:

            enquiry_id = enquiry["id"]
            name = enquiry["name"] or "Unknown name"
            source = enquiry["source"] or "Unknown source"
            programme = enquiry["programme"] or "Unknown"
            status = enquiry["status"] or "New"

            with st.expander(
                f"{name}  •  {source}  •  Status: {status}",
                expanded=False
            ):

                st.caption(
                    f"Enquiry ID: {enquiry_id}  ·  "
                    f"Programme: {programme}"
                )

                col1, col2 = st.columns(2)

                with col1:
                    st.text_input(
                        "Customer Name",
                        value=name,
                        disabled=True,
                        key=f"view_name_{enquiry_id}"
                    )

                    st.text_input(
                        "Phone Number",
                        value=enquiry["phone"] or "",
                        disabled=True,
                        key=f"view_phone_{enquiry_id}"
                    )

                    st.text_input(
                        "Source",
                        value=source,
                        disabled=True,
                        key=f"view_source_{enquiry_id}"
                    )

                with col2:
                    st.text_input(
                        "Programme",
                        value=programme,
                        disabled=True,
                        key=f"view_programme_{enquiry_id}"
                    )

                    st.text_input(
                        "Language",
                        value=enquiry["language"] or "",
                        disabled=True,
                        key=f"view_language_{enquiry_id}"
                    )

                    st.text_input(
                        "Saved At (UTC)",
                        value=str(enquiry["created_at"] or ""),
                        disabled=True,
                        key=f"view_date_{enquiry_id}"
                    )

                st.divider()

                # UPDATE STATUS
                st.markdown("**Change Enquiry Status**")

                status_col, update_col = st.columns([3, 1])

                with status_col:
                    selected_status = st.selectbox(
                        "Status",
                        STATUSES,
                        index=(
                            STATUSES.index(status)
                            if status in STATUSES else 0
                        ),
                        key=f"status_{enquiry_id}",
                        label_visibility="collapsed"
                    )

                with update_col:
                    if st.button(
                        "Update Status",
                        key=f"update_{enquiry_id}",
                        disabled=(selected_status == status),
                        use_container_width=True
                    ):

                        updated = update_enquiry_status(
                            enquiry_id,
                            selected_status
                        )

                        if updated:
                            st.rerun()
                        else:
                            st.error("Could not update status.")

                st.divider()

                # ACTION BUTTONS
                view_col, edit_col, delete_col = st.columns(3)

                with view_col:
                    if st.button(
                        "View Message",
                        key=f"view_btn_{enquiry_id}",
                        use_container_width=True
                    ):

                        key = f"view_open_{enquiry_id}"
                        st.session_state[key] = not (
                            st.session_state.get(key, False)
                        )
                        st.rerun()

                with edit_col:
                    if st.button(
                        "Edit",
                        key=f"edit_btn_{enquiry_id}",
                        use_container_width=True
                    ):

                        key = f"edit_open_{enquiry_id}"
                        st.session_state[key] = not (
                            st.session_state.get(key, False)
                        )

                        if st.session_state[key]:
                            for field in [
                                "name",
                                "phone",
                                "source",
                                "programme",
                                "language"
                            ]:
                                st.session_state.pop(
                                    f"edit_{enquiry_id}_{field}",
                                    None
                                )

                        st.rerun()

                with delete_col:
                    if st.button(
                        "Delete",
                        key=f"delete_btn_{enquiry_id}",
                        use_container_width=True
                    ):

                        key = f"delete_open_{enquiry_id}"
                        st.session_state[key] = not (
                            st.session_state.get(key, False)
                        )
                        st.rerun()

                # VIEW MESSAGE
                if st.session_state.get(
                    f"view_open_{enquiry_id}", False
                ):

                    st.text_area(
                        "Original Customer Message",
                        value=enquiry["message"] or "",
                        disabled=True,
                        height=110,
                        key=f"original_{enquiry_id}"
                    )

                    st.text_area(
                        "Saved AI Reply",
                        value=enquiry["suggested_reply"] or "",
                        disabled=True,
                        height=110,
                        key=f"reply_{enquiry_id}"
                    )

                # EDIT CUSTOMER INFORMATION
                if st.session_state.get(
                    f"edit_open_{enquiry_id}", False
                ):

                    with st.form(
                        key=f"edit_form_{enquiry_id}"
                    ):

                        edited_name = st.text_input(
                            "Customer Name",
                            value=enquiry["name"] or "",
                            key=f"edit_{enquiry_id}_name"
                        )

                        edited_phone = st.text_input(
                            "Phone Number",
                            value=enquiry["phone"] or "",
                            key=f"edit_{enquiry_id}_phone"
                        )

                        edited_source = st.selectbox(
                            "Source",
                            SOURCES,
                            index=(
                                SOURCES.index(enquiry["source"])
                                if enquiry["source"] in SOURCES
                                else 0
                            ),
                            key=f"edit_{enquiry_id}_source"
                        )

                        edited_programme = st.selectbox(
                            "Programme",
                            PROGRAMMES,
                            index=(
                                PROGRAMMES.index(enquiry["programme"])
                                if enquiry["programme"] in PROGRAMMES
                                else 0
                            ),
                            key=f"edit_{enquiry_id}_programme"
                        )

                        edited_language = st.text_input(
                            "Language",
                            value=enquiry["language"] or "",
                            key=f"edit_{enquiry_id}_language"
                        )

                        if st.form_submit_button(
                            "Save Changes"
                        ):

                            updated = update_enquiry(
                                enquiry_id,
                                edited_name,
                                edited_phone,
                                edited_source,
                                edited_programme,
                                edited_language
                            )

                            if updated:
                                st.session_state[
                                    f"edit_open_{enquiry_id}"
                                ] = False
                                st.rerun()
                            else:
                                st.error(
                                    "Could not update enquiry."
                                )

                # DELETE CONFIRMATION
                if st.session_state.get(
                    f"delete_open_{enquiry_id}", False
                ):

                    st.warning(
                        f"Delete enquiry {name}? "
                        "This action cannot be undone."
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:
                        if st.button(
                            "Confirm Delete",
                            key=f"confirm_{enquiry_id}",
                            type="primary",
                            use_container_width=True
                        ):

                            deleted = delete_enquiry(enquiry_id)

                            if deleted:
                                st.session_state.pop(
                                    f"delete_open_{enquiry_id}",
                                    None
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "Enquiry not found."
                                )

                    with cancel_col:
                        if st.button(
                            "Cancel",
                            key=f"cancel_{enquiry_id}",
                            use_container_width=True
                        ):

                            st.session_state[
                                f"delete_open_{enquiry_id}"
                            ] = False
                            st.rerun()


# ========================================
# ENQUIRY TRACKER
# ========================================

elif page == "Enquiry Tracker":

    st.title("Enquiry Tracker")
    columns = st.columns(5)

    for column, status in zip(columns, STATUSES):

        status_records = [
            enquiry
            for enquiry in records
            if enquiry["status"] == status
        ]

        with column:
            st.subheader(status)

            st.metric(
                "Enquiries",
                len(status_records)
            )

            for enquiry in status_records:

                source = escape(
                    str(enquiry["source"] or "Unknown")
                )

                programme = escape(
                    str(enquiry["programme"] or "Unknown")
                )

                name = escape(
                    str(enquiry["name"] or "Unknown name")
                )

                with st.container(border=True):

                    st.markdown(
                        f"<div class='tracker-name'>{name}</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<div class='tracker-detail'>"
                        f"Source: {source}"
                        "</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        "<div class='tracker-detail'>"
                        f"Programme: {programme}"
                        "</div>",
                        unsafe_allow_html=True
                    )