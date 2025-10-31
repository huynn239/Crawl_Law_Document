@echo off
echo ========================================
echo FULL WORKFLOW: Crawl to Supabase
echo ========================================
echo.

echo [1/4] Crawling hyperlinks (page 1-2)...
python -m tvpl_crawler links-basic -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" -o data/links.json --start-page 1 --end-page 2
if errorlevel 1 goto error
echo ✓ Done! Found links in data/links.json
echo.

echo [2/4] Crawling documents...
python crawl_data_fast.py data/links.json data/result.json
if errorlevel 1 goto error
echo ✓ Done! Documents saved to data/result.json
echo.

echo [3/4] Transforming to Supabase format...
python supabase_transform.py data/result.json
if errorlevel 1 goto error
echo ✓ Done! Transformed data in data/result_supabase.json
echo.

echo [4/4] Importing to Supabase...
python test_supabase_import.py
if errorlevel 1 goto error
echo ✓ Done! Data imported to Supabase
echo.

echo ========================================
echo ✅ WORKFLOW COMPLETED SUCCESSFULLY!
echo ========================================
goto end

:error
echo.
echo ❌ ERROR: Workflow failed at step above
echo Please check the error message and try again
exit /b 1

:end
