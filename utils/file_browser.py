"""
File Browser Component

Provides Streamlit UI components for browsing and selecting directories.
Supports local filesystem and network shares.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, List, Dict
import logging

from utils.network_discovery import (
    list_directory,
    get_home_directory,
    get_common_locations
)

logger = logging.getLogger(__name__)


def show_file_browser(
    key: str,
    initial_path: Optional[str] = None,
    mode: str = "directory"
) -> Optional[str]:
    """
    Display an interactive file/directory browser in Streamlit.

    Args:
        key: Unique key for this browser instance
        initial_path: Starting path (defaults to home directory)
        mode: "directory" or "file" - what can be selected

    Returns:
        Selected path as string, or None if nothing selected
    """
    # Initialize session state for this browser
    browser_key = f"browser_{key}"
    path_key = f"browser_path_{key}"
    selected_key = f"browser_selected_{key}"

    if browser_key not in st.session_state:
        st.session_state[browser_key] = True

    if path_key not in st.session_state:
        if initial_path and Path(initial_path).exists():
            st.session_state[path_key] = initial_path
        else:
            st.session_state[path_key] = get_home_directory()

    if selected_key not in st.session_state:
        st.session_state[selected_key] = None

    current_path = st.session_state[path_key]

    # Browser UI
    with st.container():
        st.markdown("#### 📁 Browse Filesystem")

        # Navigation bar
        col1, col2, col3 = st.columns([1, 3, 1])

        with col1:
            # Up directory button
            parent_path = str(Path(current_path).parent)
            if st.button("⬆️ Up", key=f"{key}_up", use_container_width=True):
                if parent_path != current_path:  # Not at root
                    st.session_state[path_key] = parent_path
                    st.rerun()

        with col2:
            # Current path display
            st.text_input(
                "Current Path",
                value=current_path,
                key=f"{key}_path_display",
                disabled=True,
                label_visibility="collapsed"
            )

        with col3:
            # Home button
            if st.button("🏠 Home", key=f"{key}_home", use_container_width=True):
                st.session_state[path_key] = get_home_directory()
                st.rerun()

        # Quick access locations
        st.markdown("##### Quick Access")
        locations = get_common_locations()

        # Show in 4 columns
        cols = st.columns(4)
        for idx, loc in enumerate(locations):
            with cols[idx % 4]:
                if st.button(
                    f"{loc['icon']} {loc['name']}",
                    key=f"{key}_loc_{idx}",
                    use_container_width=True
                ):
                    st.session_state[path_key] = loc['path']
                    st.rerun()

        st.markdown("---")

        # List directory contents
        st.markdown("##### Contents")

        try:
            items = list_directory(current_path, show_hidden=False)

            if not items:
                st.info("📂 Empty directory")
            else:
                # Show directories first, then files
                directories = [item for item in items if item['is_dir']]
                files = [item for item in items if not item['is_dir']]

                # Display directories
                if directories:
                    st.markdown("**Folders:**")
                    for item in directories[:50]:  # Limit to 50 items
                        col1, col2 = st.columns([4, 1])

                        with col1:
                            # Folder name with icon
                            folder_name = f"📁 {item['name']}"
                            if not item['readable']:
                                folder_name += " 🔒"

                            st.text(folder_name)

                        with col2:
                            # Buttons for navigation and selection
                            button_col1, button_col2 = st.columns(2)

                            with button_col1:
                                if st.button("➡️", key=f"{key}_open_{item['path']}", help="Open"):
                                    st.session_state[path_key] = item['path']
                                    st.rerun()

                            with button_col2:
                                if st.button("✓", key=f"{key}_select_{item['path']}", help="Select"):
                                    st.session_state[selected_key] = item['path']
                                    st.success(f"Selected: {item['path']}")
                                    return item['path']

                    if len(directories) > 50:
                        st.info(f"📊 Showing first 50 of {len(directories)} folders")

                # Display files (only in file mode)
                if mode == "file" and files:
                    st.markdown("**Files:**")
                    for item in files[:30]:  # Limit to 30 files
                        col1, col2, col3 = st.columns([3, 1, 1])

                        with col1:
                            file_name = f"📄 {item['name']}"
                            if not item['readable']:
                                file_name += " 🔒"
                            st.text(file_name)

                        with col2:
                            st.caption(item['size'])

                        with col3:
                            if st.button("✓", key=f"{key}_select_file_{item['path']}", help="Select"):
                                st.session_state[selected_key] = item['path']
                                st.success(f"Selected: {item['path']}")
                                return item['path']

                    if len(files) > 30:
                        st.info(f"📊 Showing first 30 of {len(files)} files")

        except PermissionError:
            st.error("🔒 Permission denied - Cannot access this directory")
        except Exception as e:
            st.error(f"❌ Error reading directory: {str(e)}")
            logger.error(f"Browser error for {current_path}: {e}")

        st.markdown("---")

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Select Current Directory", key=f"{key}_select_current", use_container_width=True):
                st.session_state[selected_key] = current_path
                st.success(f"Selected: {current_path}")
                return current_path

        with col2:
            if st.button("❌ Cancel", key=f"{key}_cancel", use_container_width=True):
                st.session_state[selected_key] = None
                return None

    return st.session_state.get(selected_key)


def show_network_shares_selector(key: str) -> Optional[str]:
    """
    Display a selector for mounted network shares.

    Args:
        key: Unique key for this selector

    Returns:
        Selected network share path, or None
    """
    from utils.network_discovery import get_mounted_volumes

    st.markdown("##### 🌐 Mounted Network Shares")

    mounted = get_mounted_volumes()

    if not mounted:
        st.info("No network shares currently mounted")
        st.caption("Mount a network share in Finder (⌘K) and it will appear here")
        return None

    # Display mounted shares as cards
    for idx, share in enumerate(mounted):
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                # Share name and type
                type_icon = "🌐" if share['type'] == 'smb' else "💾" if share['type'] == 'local' else "📡"
                st.markdown(f"**{type_icon} {share['name']}**")
                st.caption(share['path'])

            with col2:
                # Size info
                st.caption(f"💾 {share['available']} available of {share['size']}")

            with col3:
                # Select button
                if st.button("Select", key=f"{key}_share_{idx}", use_container_width=True):
                    return share['path']

            st.markdown("---")

    return None


def show_smb_discovery(key: str) -> Optional[List[Dict[str, str]]]:
    """
    Display SMB network discovery interface.

    Args:
        key: Unique key for this component

    Returns:
        List of discovered shares, or None
    """
    from utils.network_discovery import discover_smb_shares

    st.markdown("##### 🔍 Discover Network Shares")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.info("Scan your local network for SMB/CIFS file shares (takes 5-10 seconds)")

    with col2:
        if st.button("🔍 Scan Network", key=f"{key}_scan", use_container_width=True):
            with st.spinner("Scanning network for SMB shares..."):
                discovered = discover_smb_shares(timeout=10)

                if discovered:
                    st.success(f"Found {len(discovered)} shares!")

                    for idx, share in enumerate(discovered):
                        st.markdown(f"**🌐 {share['name']}**")
                        st.caption(f"Address: {share['address']}")
                        st.caption("Connect via Finder (⌘K) using: `smb://{}`".format(share['address']))
                        st.markdown("---")

                    return discovered
                else:
                    st.warning("No SMB shares found on the network")
                    return []

    return None


def show_path_input_with_browser(
    label: str,
    placeholder: str,
    help_text: str,
    key: str,
    initial_value: str = "",
    show_network_shares: bool = True
) -> str:
    """
    Display a path input field with integrated browse button and network share discovery.

    Args:
        label: Label for the input field
        placeholder: Placeholder text
        help_text: Help text
        key: Unique key for this component
        initial_value: Initial path value
        show_network_shares: Whether to show network shares section

    Returns:
        Selected path as string
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        path_value = st.text_input(
            label,
            value=initial_value,
            placeholder=placeholder,
            help=help_text,
            key=f"{key}_input"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Align button with input
        browse_clicked = st.button("📁 Browse", key=f"{key}_browse_btn", use_container_width=True)

    # Show browser in expander if browse clicked
    if browse_clicked or st.session_state.get(f"{key}_show_browser", False):
        st.session_state[f"{key}_show_browser"] = True

        with st.expander("📂 File Browser", expanded=True):
            # Show network shares if enabled
            if show_network_shares:
                selected_share = show_network_shares_selector(f"{key}_shares")
                if selected_share:
                    st.session_state[f"{key}_show_browser"] = False
                    return selected_share

                st.markdown("---")

            # Show file browser
            selected_path = show_file_browser(
                key=f"{key}_browser",
                initial_path=path_value if path_value else None,
                mode="directory"
            )

            if selected_path:
                st.session_state[f"{key}_show_browser"] = False
                return selected_path

    return path_value
