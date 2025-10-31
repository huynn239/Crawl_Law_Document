# -*- coding: utf-8 -*-
"""Extract document data using Selenium with undetected-chromedriver"""
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_doc_info(driver):
    """Extract document metadata from tab1"""
    doc_info = {}
    try:
        # Wait for content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tab1"))
        )
        
        # Extract fields
        fields = {
            "Số hiệu": "//div[@id='tab1']//p[contains(text(),'Số hiệu')]/following-sibling::p",
            "Loại văn bản": "//div[@id='tab1']//p[contains(text(),'Loại văn bản')]/following-sibling::p",
            "Nơi ban hành": "//div[@id='tab1']//p[contains(text(),'Nơi ban hành')]/following-sibling::p",
            "Người ký": "//div[@id='tab1']//p[contains(text(),'Người ký')]/following-sibling::p",
            "Ngày ban hành": "//div[@id='tab1']//p[contains(text(),'Ngày ban hành')]/following-sibling::p",
        }
        
        for key, xpath in fields.items():
            try:
                element = driver.find_element(By.XPATH, xpath)
                doc_info[key] = element.text.strip()
            except:
                doc_info[key] = ""
                
    except Exception as e:
        print(f"  Error extracting doc_info: {e}")
    
    return doc_info

def extract_tab4_relations(driver):
    """Extract relations from tab4"""
    relations = {}
    total = 0
    
    try:
        # Click tab4
        tab4_link = driver.find_element(By.ID, "aLuocDo")
        tab4_link.click()
        time.sleep(2)
        
        # Wait for tab4 content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tab4"))
        )
        
        # Extract relations
        relation_divs = driver.find_elements(By.XPATH, "//div[@id='tab4']//div[@class='relation-group']")
        
        for div in relation_divs:
            try:
                title = div.find_element(By.TAG_NAME, "h3").text.strip()
                links = div.find_elements(By.TAG_NAME, "a")
                
                relation_list = []
                for link in links:
                    relation_list.append({
                        "text": link.text.strip(),
                        "href": link.get_attribute("href")
                    })
                
                if relation_list:
                    relations[title] = relation_list
                    total += len(relation_list)
                    
            except:
                continue
                
    except Exception as e:
        print(f"  Error extracting tab4: {e}")
    
    return relations, total

def extract_tab8_files(driver):
    """Extract download links from tab8"""
    files = []
    
    try:
        # Click tab8
        tab8_link = driver.find_element(By.ID, "aTabTaiVe")
        tab8_link.click()
        time.sleep(2)
        
        # Wait for tab8 content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tab8"))
        )
        
        # Extract links
        links = driver.find_elements(By.XPATH, "//div[@id='tab8']//a[@href]")
        
        for link in links:
            href = link.get_attribute("href")
            if href and not href.startswith("#"):
                files.append({
                    "text": link.text.strip(),
                    "href": href if href.startswith("http") else f"https://thuvienphapluat.vn{href}"
                })
                
    except Exception as e:
        print(f"  Error extracting tab8: {e}")
    
    return files

def _has_valid_doc_info(doc_info):
    """Check if doc_info has valid data"""
    return any(v for v in doc_info.values() if v and v != "Dữ liệu đang cập nhật")

def dismiss_popups(driver):
    """Dismiss any popups that appear during crawl"""
    try:
        # Tìm và đóng các popup (không phải popup login)
        close_selectors = [
            "button.ui-dialog-titlebar-close",  # Nút X đóng dialog
            "a.ui-dialog-titlebar-close",
            "button[aria-label='Close']",
            "button.close",
            ".modal-close",
            "[data-dismiss='modal']",
            ".ui-icon-closethick"  # jQuery UI close icon
        ]
        
        popup_closed = False
        for selector in close_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                        popup_closed = True
            except:
                continue
        
        return popup_closed
    except:
        return False

def extract_document(driver, url, timeout=30, max_retries=3):
    """Extract full document data with retry logic"""
    for attempt in range(max_retries):
        try:
            driver.get(url)
            time.sleep(random.uniform(3, 5))
            
            # Wait for Cloudflare (undetected-chromedriver tự động xử lý)
            max_wait = 60  # Tăng lên 60s để đợi user click thủ công nếu cần
            start_time = time.time()
            cloudflare_detected = False
            
            while "Verify you are human" in driver.page_source or "Just a moment" in driver.page_source:
                elapsed = time.time() - start_time
                
                if not cloudflare_detected:
                    print("    🔒 Cloudflare detected, waiting for bypass...")
                    cloudflare_detected = True
                
                if elapsed > max_wait:
                    if attempt < max_retries - 1:
                        print(f"    ⏱ Cloudflare timeout, retry {attempt+1}/{max_retries}...")
                        time.sleep(random.uniform(20, 25))
                        break
                    return {"error": "Cloudflare timeout"}
                
                # Hiển thị progress mỗi 5s
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    print(f"    ⏳ Waiting... {int(elapsed)}s/{max_wait}s")
                
                time.sleep(2)
            
            if "Verify you are human" in driver.page_source:
                continue
            
            if cloudflare_detected:
                print("    ✅ Cloudflare bypassed")
            
            time.sleep(1)
            
            # Dismiss any popups before extracting
            dismiss_popups(driver)
            
            # Extract data
            doc_info = extract_doc_info(driver)
            relations, total_relations = extract_tab4_relations(driver)
            files = extract_tab8_files(driver)
            
            # Check if data is valid
            if not _has_valid_doc_info(doc_info) and attempt < max_retries - 1:
                print(f"    Data null, retry {attempt+1}/{max_retries}...")
                time.sleep(random.uniform(20, 25))
                continue
            
            return {
                "url": url,
                "doc_info": doc_info,
                "tab4_relations": relations,
                "tab4_total_relations": total_relations,
                "tab8_links": files
            }
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    Error: {str(e)[:80]}, retry {attempt+1}/{max_retries}...")
                time.sleep(random.uniform(20, 25))
                continue
            return {"url": url, "error": str(e)}
    
    return {"url": url, "error": "Failed after retries"}
