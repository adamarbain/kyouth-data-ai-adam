import sys
import io
from pathlib import Path
from email.message import EmailMessage
from email import message_from_binary_file
import quopri

# Configure output encoding for Windows console compatibility
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def ingest_all_mhtml(input_dir: str, output_dir: str) -> dict:
    """
    Extract and decode HTML from MHTML files into raw HTML format.
    
    MHTML files are multi-part email messages containing HTML content.
    This function:
    1. Reads each .mhtml file from input_dir
    2. Parses it as an email message
    3. Extracts HTML parts and decodes quoted-printable content
    4. Saves decoded HTML to output_dir
    
    Args:
        input_dir: Path to directory containing .mhtml files
        output_dir: Path to directory where extracted .html files will be saved
    
    Returns:
        Dictionary with statistics: {'total': int, 'extracted': int, 'failed': int}
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize statistics
    total = 0
    extracted = 0
    failed = 0
    
    print("🥉 Bronze:...")
    
    # Handle case where input directory doesn't exist
    if not input_path.exists():
        print(f"⚠️ Input directory not found: {input_dir}")
        print(f"\n📊 Bronze Summary:")
        print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")
        return {"total": total, "extracted": extracted, "failed": failed}
    
    # Get all .mhtml files sorted by name
    mhtml_files = sorted(input_path.glob("*.mhtml"))
    
    if not mhtml_files:
        print(f"⚠️ No .mhtml files found in: {input_dir}")
        print(f"\n📊 Bronze Summary:")
        print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")
        return {"total": total, "extracted": extracted, "failed": failed}
    
    # Process each MHTML file
    for mhtml_file in mhtml_files:
        total += 1
        html_filename = mhtml_file.stem + ".html"
        html_output_path = output_path / html_filename
        
        try:
            # Read and parse the MHTML file as an email message
            with open(mhtml_file, "rb") as f:
                msg = message_from_binary_file(f)
            
            # Extract HTML content
            html_content = None
            
            # Try to find HTML part in multipart message
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        # Get the payload and decode if necessary
                        payload = part.get_payload(decode=True)
                        
                        if payload:
                            # Try to decode as UTF-8, fallback to latin-1
                            try:
                                html_content = payload.decode("utf-8")
                            except UnicodeDecodeError:
                                try:
                                    html_content = payload.decode("latin-1")
                                except UnicodeDecodeError:
                                    html_content = payload.decode("utf-8", errors="replace")
                            break
            else:
                # Single part message, try to extract HTML
                payload = msg.get_payload(decode=True)
                if payload:
                    try:
                        html_content = payload.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            html_content = payload.decode("latin-1")
                        except UnicodeDecodeError:
                            html_content = payload.decode("utf-8", errors="replace")
            
            # If no HTML content found, check for quoted-printable encoded content
            if not html_content:
                payload_raw = msg.get_payload()
                if isinstance(payload_raw, str) and "=" in payload_raw:
                    try:
                        html_content = quopri.decodestring(payload_raw).decode("utf-8", errors="replace")
                    except Exception:
                        pass
            
            if html_content:
                # Write the extracted HTML to file
                with open(html_output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"✅ Extracted: {mhtml_file.name}")
                extracted += 1
            else:
                print(f"⚠️ No HTML content found in: {mhtml_file.name}")
                failed += 1
        
        except Exception as e:
            print(f"⚠️ Error processing {mhtml_file.name}: {str(e)}")
            failed += 1
    
    # Print summary
    print(f"\n📊 Bronze Summary:")
    print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")
    
    return {"total": total, "extracted": extracted, "failed": failed}


if __name__ == "__main__":
    # Default paths
    input_dir = "data/0_source"
    output_dir = "data/1_bronze"
    
    ingest_all_mhtml(input_dir, output_dir)
