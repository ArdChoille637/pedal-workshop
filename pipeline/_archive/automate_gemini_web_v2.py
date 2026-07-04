import os
import time
import json
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    pipeline_dir = Path(__file__).resolve().parent
    manifest_path = pipeline_dir / "manifest.json"
    extractions_dir = pipeline_dir / "extractions"
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    pending = []
    for path, s in manifest.get("entries", {}).items():
        slug = s["slug"]
        out_file = extractions_dir / f"{slug}.json"
        if out_file.exists() and out_file.stat().st_size > 1000:
            continue
        pending.append((path, s))
            
    if not pending:
        print("No schematics pending!")
        return
        
    print(f"Found {len(pending)} pending schematics. Starting automation...")

    prompt_path = pipeline_dir / "extraction_prompt.txt"
    with open(prompt_path, "r") as f:
        prompt_text = f.read()

    async with async_playwright() as p:
        print("Connecting to Chrome via CDP...")
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        for idx, (path, s) in enumerate(pending):
            slug = s["slug"]
            image_path = Path(path)
            
            if not image_path.exists():
                print(f"[{idx+1}/{len(pending)}] Skipping {slug}: Source not found")
                continue
                
            import subprocess
            temp_image = f"/tmp/{slug}.png"
            try:
                subprocess.run(['sips', '-s', 'format', 'png', str(image_path), '--out', temp_image], check=True, capture_output=True)
                upload_path = temp_image
            except Exception as e:
                print(f"Failed to convert image with sips for {slug}: {e}. Falling back to original.")
                upload_path = str(image_path)
            
            print(f"[{idx+1}/{len(pending)}] Uploading {slug}...")
            
            # Retry page.goto up to 3 times
            goto_success = False
            for goto_attempt in range(3):
                try:
                    await page.goto("https://gemini.google.com/", timeout=60000)
                    goto_success = True
                    break
                except Exception as e:
                    print(f"Page load failed (attempt {goto_attempt+1}): {e}")
                    await asyncio.sleep(5)
                    
            if not goto_success:
                print(f"Failed to load Gemini page for {slug}. Skipping.")
                continue
                
            await asyncio.sleep(3)
            
            try:
                # Type prompt
                text_area = page.locator('div[contenteditable="true"][role="textbox"]')
                await text_area.wait_for(state="visible", timeout=10000)
                await text_area.fill(prompt_text)
                await asyncio.sleep(1)

                # Upload image
                upload_btn = page.locator('button[aria-label="Upload & tools"]')
                if await upload_btn.count() > 0:
                    await upload_btn.click(timeout=3000)
                    await asyncio.sleep(1)
                    async with page.expect_file_chooser(timeout=3000) as fc_info:
                        menu_item = page.locator('[role="menuitem"]:has-text("Upload")').first
                        await menu_item.click(timeout=3000)
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(upload_path)
                    await asyncio.sleep(2)
                else:
                    file_input = page.locator('input[type="file"]')
                    await file_input.wait_for(state="attached", timeout=5000)
                    await file_input.set_input_files(upload_path)
                    await asyncio.sleep(2)
                
                # Send
                send_button = page.locator('button[aria-label="Send message"]')
                if await send_button.count() == 0:
                     send_button = page.locator('button:has-text("Send")')
                
                if await send_button.count() > 0:
                    await send_button.first.click()
                else:
                    await text_area.press("Enter")
                    
                # Wait for generation to completely finish
                print(f"Waiting for generation for {slug}...")
                
                # Wait a minimum of 20 seconds before starting to check
                await asyncio.sleep(20)
                
                max_retries = 30 # up to ~2 minutes
                json_saved = False
                for attempt in range(max_retries):
                    responses = page.locator('message-content') 
                    if await responses.count() > 0:
                        last_response = responses.nth(-1)
                        text = await last_response.inner_text()
                        
                        # Wait until the 'issues' array is generated to ensure it is at the end
                        if "issues" in text and text.strip().endswith("}"):
                            first_brace = text.find("{")
                            last_brace = text.rfind("}")
                            if first_brace != -1 and last_brace != -1:
                                json_str = text[first_brace:last_brace+1]
                                clean_str = re.sub(r'```json\n|\n```|```', '', json_str).strip()
                                try:
                                    parsed = json.loads(clean_str)
                                    with open(extractions_dir / f"{slug}.json", "w") as out:
                                        json.dump(parsed, out, indent=2)
                                    print(f"Saved {slug}.json")
                                    json_saved = True
                                    break
                                except Exception as e:
                                    pass
                    
                    if json_saved:
                        break
                        
                    # Auto scroll down so we don't get stuck
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(4)
                
                if not json_saved:
                    print(f"Failed to fully extract JSON for {slug}. It may have timed out or failed.")
                    
            except Exception as e:
                print(f"Error processing {slug}: {e}")
            
            # Brief pause before next
            await asyncio.sleep(3)
            
if __name__ == "__main__":
    asyncio.run(main())
