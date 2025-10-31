@echo off
echo Testing crawl hyperlinks with start-page and end-page...

python -m tvpl_crawler links-basic -u "https://thuvienphapluat.vn/page/tim-van-ban.aspx?keyword=&area=0&match=True&type=0&lan=1&status=-1&org=-1&field=-1&year=2025&page={page}" -o data/links_test.json --start-page 1 --end-page 2

echo.
echo Done! Check data/links_test.json
