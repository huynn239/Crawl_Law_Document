
"""Giải CAPTCHA bằng OCR (Tesseract)"""
import asyncio
import io
import random
from PIL import Image
import pytesseract

# Đường dẫn Tesseract (Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

async def bypass_captcha(page, doc_id=0) -> bool:
    """Bypass CAPTCHA bằng OCR với logic mạnh mẽ"""
    try:
        # Tìm ảnh CAPTCHA và ô nhập
        img_locator = page.locator('#ctl00_Content_pnlLoginTemplate img')
        input_box = page.locator('#ctl00_Content_txtSecCode')
        
        img_count = await img_locator.count()
        input_count = await input_box.count()
        
        # Kiểm tra có CAPTCHA không
        if img_count > 0 and input_count > 0:
            print(f"\n[CAPTCHA] doc_id={doc_id}: 🔴 Phát hiện CAPTCHA (img={img_count}, input={input_count})")
            
            for attempt in range(5):
                print(f"[CAPTCHA] doc_id={doc_id}: 🔄 Lần thử {attempt + 1}/5...")
                try:
                    # Chụp ảnh CAPTCHA
                    buf = await img_locator.screenshot()
                    im = Image.open(io.BytesIO(buf)).convert('L')
                    
                    # Tăng chất lượng OCR
                    w, h = im.size
                    im = im.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
                    im = im.point(lambda x: 0 if x < 150 else 255, '1')
                    
                    # OCR đọc số (cho phép cả chữ và số)
                    config = '--psm 7 -c tessedit_char_whitelist=0123456789'
                    code = pytesseract.image_to_string(im, config=config)
                    code = ''.join(ch for ch in code if ch.isdigit())
                    
                    # Nếu không đọc được số, thử đọc chữ + số
                    if len(code) < 4:
                        config = '--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        code = pytesseract.image_to_string(im, config=config)
                        code = ''.join(ch for ch in code if ch.isalnum()).upper()
                    
                    if len(code) < 4:
                        print(f"[CAPTCHA] doc_id={doc_id}: ⚠ Code không hợp lệ ('{code}'), làm mới...")
                        await img_locator.click()
                        await asyncio.sleep(1.5)
                        continue
                    
                    print(f"[CAPTCHA] doc_id={doc_id}: 🔑 Đọc được code: {code}")
                    
                    # Điền code và submit
                    await input_box.fill(code)
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    
                    # Click nút xác nhận
                    submit_btn = page.locator('#ctl00_Content_cmdLogin')
                    if await submit_btn.count() > 0:
                        await submit_btn.click()
                        await page.wait_for_timeout(3000)
                        
                        # Kiểm tra thành công
                        if await img_locator.count() == 0:
                            print(f"[CAPTCHA] doc_id={doc_id}: ✅ Bypass thành công!\n")
                            return True
                        else:
                            print(f"[CAPTCHA] doc_id={doc_id}: ❌ Code sai, thử lại...")
                    
                except Exception as e:
                    print(f"[CAPTCHA] doc_id={doc_id}: Lỗi lần thử {attempt+1}: {e}")
                    await asyncio.sleep(1)
            
            print(f"[CAPTCHA] doc_id={doc_id}: ❌ Không thể bypass sau 5 lần thử.\n")
            return False
        
        # Không có CAPTCHA
        return True
        
    except Exception as e:
        print(f"[CAPTCHA] doc_id={doc_id}: Lỗi nghiêm trọng: {e}")
        return False
