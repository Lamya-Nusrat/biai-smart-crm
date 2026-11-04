
import logging
import unicodedata
from html import escape

import pandas as pd
import streamlit as st

from ai_service import extract_enquiry, generate_reply
from database import (
    get_all_enquiries,
    save_enquiry,
    update_enquiry_status,
    update_enquiry,
    delete_enquiry,
    matching_enquiries,
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

OTHER_OPTION = "Other / Add New"


# ----------------------------------------
# CUSTOM STYLING
# ----------------------------------------

st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
    max-width: 1250px;
}

/* Dashboard metric cards */

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

/* Saved enquiry cards */

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

/* Hide heading links */

[data-testid="stHeading"] a {
    visibility: hidden;
}

/* Hide chart toolbar */

[data-testid="stElementToolbar"] {
    display: none !important;
}

/* Empty-state message */

.empty-state {
    background: #FFFFFF;
    border: 1px solid #DED7CC;
    border-top: 5px solid #D45116;
    border-radius: 14px;
    padding: 20px 24px;
    color: #55504A;
    font-size: 16px;
    line-height: 1.5;
}

/* Tracker customer name */

.tracker-name {
    color: #111111;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.3;
    margin-bottom: 12px;
    overflow-wrap: anywhere;
}

/* Keep long text inside tracker cards */

.tracker-detail {
    color: #55504A;
    font-size: 12px;
    line-height: 1.5;
    margin: 4px 0;
    white-space: normal;
    overflow-wrap: anywhere;
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
    "message_input": "",
    "extracted_data": None,
    "processed_message": "",
    "suggested_reply": "",
    "reply_error": False,
    "extraction_error": False,
    "clear_after_save": False,
    "saved_notice": False
}

for key, value in initial_state.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ----------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------

def normalize_search_text(value):
    """Normalize text for searching."""

    text = unicodedata.normalize(
        "NFKC",
        str(value or "")
    )

    return " ".join(
        text.casefold().split()
    )


def matches_search(enquiry, query):
    """Search saved enquiry information."""

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


def category_options(defaults, records, field, current):
    """
    Include known categories, existing database values,
    and the value detected by AI.
    """

    values = list(defaults)

    for record in records:

        value = str(
            record.get(field) or ""
        ).strip()

        if (
            value
            and value not in values
            and value != OTHER_OPTION
        ):
            values.append(value)

    current = str(current or "").strip()

    if (
        current
        and current not in values
        and current != OTHER_OPTION
    ):
        values.append(current)

    values.append(OTHER_OPTION)

    return values


def choose_category(
    label,
    defaults,
    records,
    field,
    current,
    key_prefix
):
    """
    Select an existing Source/Programme or enter
    a new custom value.
    """

    options = category_options(
        defaults,
        records,
        field,
        current
    )

    selected = st.selectbox(
        label,
        options,
        index=(
            options.index(current)
            if current in options
            else 0
        ),
        key=f"{key_prefix}_choice"
    )

    if selected == OTHER_OPTION:

        custom_value = st.text_input(
            f"New {label}",
            placeholder="Enter a custom value",
            key=f"{key_prefix}_custom"
        )

        return custom_value.strip()

    return selected


def clear_processor():
    """
    Clear the previous enquiry after saving,
    before the message widget is displayed.
    """

    st.session_state.message_input = ""
    st.session_state.extracted_data = None
    st.session_state.processed_message = ""
    st.session_state.suggested_reply = ""

    st.session_state.reply_error = False
    st.session_state.extraction_error = False

    fields_to_clear = [
        "customer_name",
        "customer_phone",
        "customer_status",
        "customer_language",
        "reply_editor",
        "new_source_choice",
        "new_source_custom",
        "new_programme_choice",
        "new_programme_custom"
    ]

    for field in fields_to_clear:
        st.session_state.pop(field, None)

    st.session_state.clear_after_save = False


def reset_extraction_fields():
    """Clear previous AI form fields."""

    fields = [
        "customer_name",
        "customer_phone",
        "customer_status",
        "customer_language",
        "reply_editor",
        "new_source_choice",
        "new_source_custom",
        "new_programme_choice",
        "new_programme_custom"
    ]

    for field in fields:
        st.session_state.pop(field, None)


# Load database records
records = get_all_enquiries()


# ========================================
# DASHBOARD
# ========================================

if page == "Dashboard":

    st.title("Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Enquiries",
        len(records)
    )

    col2.metric(
        "New",
        sum(
            enquiry["status"] == "New"
            for enquiry in records
        )
    )

    col3.metric(
        "Interested",
        sum(
            enquiry["status"] == "Interested"
            for enquiry in records
        )
    )

    st.subheader("Pipeline Overview")

    chart_data = pd.DataFrame(
        {
            "Enquiries": [
                sum(
                    enquiry["status"] == status
                    for enquiry in records
                )
                for status in STATUSES
            ]
        },
        index=STATUSES
    )

    st.bar_chart(
        chart_data,
        color="#D45116"
    )


# ========================================
# AI ENQUIRY ASSISTANT
# ========================================

elif page == "AI Enquiry Assistant":

    # Clear previous enquiry after successful save
    if st.session_state.clear_after_save:
        clear_processor()

    st.title("AI Enquiry Assistant")

    if st.session_state.pop("saved_notice", False):

        st.success(
            "Enquiry saved successfully! "
            "You can paste a new enquiry."
        )

    message = st.text_area(
        "Paste Customer Enquiry",
        height=180,
        key="message_input"
    )

    if st.button(
        "Extract Information with AI",
        type="primary"
    ):

        if not message.strip():

            st.warning(
                "Please paste an enquiry first."
            )

        else:

            reset_extraction_fields()

            st.session_state.extracted_data = None
            st.session_state.processed_message = ""
            st.session_state.suggested_reply = ""
            st.session_state.reply_error = False
            st.session_state.extraction_error = False

            try:

                with st.spinner(
                    "Extracting information..."
                ):

                    result = extract_enquiry(message)

                st.session_state.extracted_data = result
                st.session_state.processed_message = message

                try:

                    with st.spinner(
                        "Generating suggested reply..."
                    ):

                        reply = generate_reply(
                            message,
                            result.get("language") or "English",
                            result.get("name")
                        )

                    st.session_state.suggested_reply = reply

                except Exception:

                    logging.exception(
                        "Reply generation failed"
                    )

                    st.session_state.reply_error = True

            except Exception:

                logging.exception(
                    "Enquiry extraction failed"
                )

                st.session_state.extraction_error = True

    if st.session_state.extraction_error:

        st.error(
            "Unable to extract enquiry information "
            "right now. Please try again."
        )

    result = st.session_state.extracted_data

    if (
        result is not None
        and st.session_state.processed_message == message
    ):

        st.success(
            "Information extracted successfully!"
        )

        if st.session_state.reply_error:

            st.warning(
                "A suggested reply could not be generated. "
                "You can write a reply manually below "
                "or try extracting again."
            )

        initial_fields = {
            "customer_name": result.get("name") or "",
            "customer_phone": result.get("phone") or "",
            "customer_status": "New",
            "customer_language": (
                result.get("language") or "English"
            ),
            "reply_editor": st.session_state.suggested_reply
        }

        for field, value in initial_fields.items():

            if field not in st.session_state:
                st.session_state[field] = value

        st.subheader(
            "Extracted Customer Information"
        )

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

            selected_source = choose_category(
                label="Enquiry Source",
                defaults=SOURCES,
                records=records,
                field="source",
                current=(
                    result.get("source") or "Unknown"
                ),
                key_prefix="new_source"
            )

        with col2:

            selected_programme = choose_category(
                label="Interested Programme",
                defaults=PROGRAMMES,
                records=records,
                field="programme",
                current=(
                    result.get("programme") or "Unknown"
                ),
                key_prefix="new_programme"
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

        duplicates = matching_enquiries(
            st.session_state.customer_phone,
            st.session_state.processed_message
        )

        if duplicates:

            st.warning(
                "This enquiry may already be saved. "
                "You can still save it again if needed."
            )

        if st.button(
            "Save Enquiry",
            type="primary"
        ):

            if (
                not selected_source
                or not selected_programme
            ):

                st.warning(
                    "Enter a source and programme, "
                    "or choose Unknown."
                )

            else:

                try:

                    save_enquiry(
                        st.session_state.customer_name,
                        st.session_state.customer_phone,
                        selected_source,
                        selected_programme,
                        st.session_state.customer_status,
                        st.session_state.customer_language,
                        st.session_state.processed_message,
                        st.session_state.reply_editor
                    )

                    st.session_state.saved_notice = True
                    st.session_state.clear_after_save = True

                    st.rerun()

                except Exception:

                    logging.exception(
                        "Saving enquiry failed"
                    )

                    st.error(
                        "Unable to save the enquiry. "
                        "Please try again."
                    )

    elif (
        result is not None
        and message != st.session_state.processed_message
    ):

        st.caption(
            "Message changed. Click Extract Information "
            "with AI to process the new enquiry."
        )


# ========================================
# SAVED ENQUIRIES
# ========================================

elif page == "Enquiries":

    st.title("Saved Enquiries")

    if not records:

        st.markdown(
            '<div class="empty-state">'
            'No enquiries saved yet.'
            '</div>',
            unsafe_allow_html=True
        )

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

        st.caption(
            "Click an enquiry below to view details, "
            "update its status, edit or delete it."
        )

        if not filtered_records:

            st.markdown(
                '<div class="empty-state">'
                'No matching enquiries found.'
                '</div>',
                unsafe_allow_html=True
            )

        for enquiry in filtered_records:

            enquiry_id = enquiry["id"]

            name = (
                enquiry["name"] or "Unknown name"
            )

            source = (
                enquiry["source"] or "Unknown"
            )

            programme = (
                enquiry["programme"] or "Unknown"
            )

            status = (
                enquiry["status"] or "New"
            )

            with st.expander(
                f"{name}  •  {source}  •  Status: {status}"
            ):

                st.caption(
                    f"Programme: {programme}"
                )

                left, right = st.columns(2)

                with left:

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

                with right:

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
                        value=str(
                            enquiry["created_at"] or ""
                        ),
                        disabled=True,
                        key=f"view_date_{enquiry_id}"
                    )

                st.divider()

                # UPDATE STATUS

                st.markdown(
                    "**Change Enquiry Status**"
                )

                status_col, update_col = st.columns(
                    [3, 1]
                )

                with status_col:

                    selected_status = st.selectbox(
                        "Status",
                        STATUSES,
                        index=(
                            STATUSES.index(status)
                            if status in STATUSES
                            else 0
                        ),
                        key=f"status_{enquiry_id}",
                        label_visibility="collapsed"
                    )

                with update_col:

                    if st.button(
                        "Update Status",
                        key=f"status_btn_{enquiry_id}",
                        disabled=(
                            selected_status == status
                        ),
                        use_container_width=True
                    ):

                        update_enquiry_status(
                            enquiry_id,
                            selected_status
                        )

                        st.rerun()

                st.divider()

                # VIEW, EDIT, DELETE BUTTONS

                view_col, edit_col, delete_col = (
                    st.columns(3)
                )

                with view_col:

                    if st.button(
                        "View Message",
                        key=f"view_btn_{enquiry_id}",
                        use_container_width=True
                    ):

                        key = (
                            f"show_message_{enquiry_id}"
                        )

                        st.session_state[key] = not (
                            st.session_state.get(
                                key, False
                            )
                        )

                        st.rerun()

                with edit_col:

                    if st.button(
                        "Edit",
                        key=f"edit_btn_{enquiry_id}",
                        use_container_width=True
                    ):

                        key = (
                            f"edit_open_{enquiry_id}"
                        )

                        st.session_state[key] = not (
                            st.session_state.get(
                                key, False
                            )
                        )

                        if st.session_state[key]:

                            for item in [
                                "name",
                                "phone",
                                "language",
                                "reply"
                            ]:

                                st.session_state.pop(
                                    f"edit_{enquiry_id}_{item}",
                                    None
                                )

                            for item in [
                                "source",
                                "programme"
                            ]:

                                st.session_state.pop(
                                    f"edit_{enquiry_id}_{item}_choice",
                                    None
                                )

                                st.session_state.pop(
                                    f"edit_{enquiry_id}_{item}_custom",
                                    None
                                )

                        st.rerun()

                with delete_col:

                    if st.button(
                        "Delete",
                        key=f"delete_btn_{enquiry_id}",
                        use_container_width=True
                    ):

                        key = (
                            f"delete_open_{enquiry_id}"
                        )

                        st.session_state[key] = not (
                            st.session_state.get(
                                key, False
                            )
                        )

                        st.rerun()

                # VIEW ORIGINAL MESSAGE AND REPLY

                if st.session_state.get(
                    f"show_message_{enquiry_id}",
                    False
                ):

                    st.text_area(
                        "Original Customer Message",
                        value=(
                            enquiry["message"] or ""
                        ),
                        disabled=True,
                        height=110,
                        key=f"original_{enquiry_id}"
                    )

                    st.text_area(
                        "Saved Reply",
                        value=(
                            enquiry["suggested_reply"] or ""
                        ),
                        disabled=True,
                        height=110,
                        key=f"saved_reply_{enquiry_id}"
                    )

                # EDIT ENQUIRY

                if st.session_state.get(
                    f"edit_open_{enquiry_id}",
                    False
                ):

                    st.markdown(
                        "**Edit Enquiry**"
                    )

                    edit_left, edit_right = (
                        st.columns(2)
                    )

                    with edit_left:

                        edited_name = st.text_input(
                            "Customer Name",
                            value=(
                                enquiry["name"] or ""
                            ),
                            key=f"edit_{enquiry_id}_name"
                        )

                        edited_phone = st.text_input(
                            "Phone Number",
                            value=(
                                enquiry["phone"] or ""
                            ),
                            key=f"edit_{enquiry_id}_phone"
                        )

                        edited_source = choose_category(
                            label="Source",
                            defaults=SOURCES,
                            records=records,
                            field="source",
                            current=source,
                            key_prefix=(
                                f"edit_{enquiry_id}_source"
                            )
                        )

                    with edit_right:

                        edited_programme = choose_category(
                            label="Programme",
                            defaults=PROGRAMMES,
                            records=records,
                            field="programme",
                            current=programme,
                            key_prefix=(
                                f"edit_{enquiry_id}_programme"
                            )
                        )

                        edited_language = st.text_input(
                            "Language",
                            value=(
                                enquiry["language"] or ""
                            ),
                            key=f"edit_{enquiry_id}_language"
                        )

                    edited_reply = st.text_area(
                        "Suggested Reply",
                        value=(
                            enquiry["suggested_reply"] or ""
                        ),
                        height=110,
                        key=f"edit_{enquiry_id}_reply"
                    )

                    if st.button(
                        "Save Changes",
                        key=f"save_changes_{enquiry_id}",
                        type="primary"
                    ):

                        if (
                            not edited_source
                            or not edited_programme
                        ):

                            st.warning(
                                "Enter a source and programme, "
                                "or choose Unknown."
                            )

                        else:

                            try:

                                update_enquiry(
                                    enquiry_id,
                                    edited_name,
                                    edited_phone,
                                    edited_source,
                                    edited_programme,
                                    edited_language,
                                    edited_reply
                                )

                                st.session_state[
                                    f"edit_open_{enquiry_id}"
                                ] = False

                                st.rerun()

                            except Exception:

                                logging.exception(
                                    "Update failed"
                                )

                                st.error(
                                    "Unable to update the enquiry. "
                                    "Please try again."
                                )

                # DELETE CONFIRMATION

                if st.session_state.get(
                    f"delete_open_{enquiry_id}",
                    False
                ):

                    st.warning(
                        f"Delete enquiry for {name}? "
                        "This cannot be undone."
                    )

                    confirm_col, cancel_col = (
                        st.columns(2)
                    )

                    with confirm_col:

                        if st.button(
                            "Confirm Delete",
                            key=f"confirm_{enquiry_id}",
                            type="primary",
                            use_container_width=True
                        ):

                            delete_enquiry(
                                enquiry_id
                            )

                            st.rerun()

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

    for column, status in zip(
        columns,
        STATUSES
    ):

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

                name = escape(
                    str(
                        enquiry["name"]
                        or "Unknown name"
                    )
                )

                source = escape(
                    str(
                        enquiry["source"]
                        or "Unknown"
                    )
                )

                programme = escape(
                    str(
                        enquiry["programme"]
                        or "Unknown"
                    )
                )

                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"<div class='tracker-name'>"
                        f"{name}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<div class='tracker-detail'>"
                        f"Source: {source}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        f"<div class='tracker-detail'>"
                        f"Programme: {programme}"
                        f"</div>",
                        unsafe_allow_html=True
                    )