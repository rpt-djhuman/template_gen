# utils/document_utils.py
import streamlit as st
import tempfile
import os
from docling.document_converter import DocumentConverter


# @st.cache_resource
def get_document_converter():
    """Cache the DocumentConverter to prevent reloading on each interaction"""
    return None  # Return None initially


def get_or_create_document_converter():
    """Get existing converter or create a new one only when needed"""
    converter = get_document_converter()
    if converter is None:
        converter = DocumentConverter()
        # Update the cached value
        get_document_converter._cached_obj = converter
    return converter


@st.cache_data
def parse_documents(uploaded_files):
    """Parse multiple document files and extract their text content."""
    if not uploaded_files:
        return ""

    import tempfile
    import os

    converter = get_or_create_document_converter()
    content = ""

    for file in uploaded_files:
        try:
            file_type = file.name.split(".")[-1].lower()

            # Handle text files directly
            if file_type == "txt":
                content += file.getvalue().decode("utf-8")
            # Use converter for other supported file types
            elif file_type in ["pdf", "docx", "html"]:
                # Create a temporary file with the correct extension
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f".{file_type}"
                ) as tmp_file:
                    # Write the uploaded file content to the temp file
                    tmp_file.write(file.getvalue())
                    tmp_path = tmp_file.name

                # Convert using the file path instead of the UploadedFile object
                source = converter.convert(tmp_path)
                content += source.document.export_to_markdown()

                # Clean up the temporary file
                os.unlink(tmp_path)
            else:
                st.warning(f"Unsupported file type: {file.name}")
        except Exception as e:
            st.error(f"Error processing file {file.name}: {str(e)}")

    return content
