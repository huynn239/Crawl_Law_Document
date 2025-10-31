#!/usr/bin/env python3
"""
Hybrid Formula Crawler - Combines Crawl4AI + Regex + LLM
Enhanced version of crawl_formulas_fast.py with Crawl4AI integration
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Import the hybrid extractor
from hybrid_formula_extractor import HybridFormulaExtractor

async def crawl_formulas_hybrid(input_file: str, output_file: str = None, method: str = "hybrid"):
    """
    Crawl formulas using hybrid approach (Crawl4AI + Regex + LLM)
    
    Args:
        input_file: JSON file with URLs
        output_file: Output file (optional)
        method: "hybrid" (Crawl4AI+Regex+LLM) or "regex" (Regex+LLM only)
    """
    
    # Load environment
    load_dotenv()
    
    # Setup output file
    if not output_file:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_hybrid_formulas.json")
    
    # Initialize extractor
    openai_key = os.getenv('OPENAI_API_KEY')
    use_crawl4ai = method == "hybrid"
    
    extractor = HybridFormulaExtractor(
        openai_api_key=openai_key,
        use_crawl4ai=use_crawl4ai
    )
    
    # Load input URLs
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            links_data = json.load(f)
            
        # Extract URLs
        if isinstance(links_data, list):
            if all(isinstance(item, dict) and 'Url' in item for item in links_data):
                urls = [item['Url'] for item in links_data]
            else:
                urls = [item for item in links_data if isinstance(item, str)]
        else:
            urls = [input_file]  # Single URL
            
        logger.info(f"Processing {len(urls)} URLs with {method} method")
        
    except Exception as e:
        logger.error(f"Failed to load input file: {e}")
        return
    
    # Process URLs
    results = []
    
    for i, url in enumerate(urls, 1):
        logger.info(f"Processing {i}/{len(urls)}: {url}")
        
        try:
            if use_crawl4ai:
                # Use Crawl4AI + hybrid approach
                result = await extractor.extract_from_url(url)
            else:
                # Fallback: manual content input required
                logger.warning(f"Crawl4AI disabled, skipping URL: {url}")
                result = {
                    'url': url,
                    'formulas': [],
                    'parameters': [],
                    'total_formulas': 0,
                    'total_parameters': 0,
                    'extraction_method': 'skipped_no_crawl4ai',
                    'error': 'Crawl4AI disabled, manual content required'
                }
            
            results.append(result)
            
            # Progress update
            if result.get('total_formulas', 0) > 0:
                logger.success(f"✅ Found {result['total_formulas']} formulas, {result.get('total_parameters', 0)} parameters")
            else:
                logger.warning(f"⚠️ No formulas found")
                
        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
            results.append({
                'url': url,
                'formulas': [],
                'parameters': [],
                'total_formulas': 0,
                'total_parameters': 0,
                'extraction_method': 'failed',
                'error': str(e)
            })
    
    # Save results
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Summary
        total_formulas = sum(r.get('total_formulas', 0) for r in results)
        total_parameters = sum(r.get('total_parameters', 0) for r in results)
        successful = len([r for r in results if r.get('total_formulas', 0) > 0])
        
        logger.success(f"🎉 Hybrid crawling completed!")
        logger.info(f"📊 Total: {total_formulas} formulas, {total_parameters} parameters")
        logger.info(f"✅ Success rate: {successful}/{len(urls)} ({successful/len(urls)*100:.1f}%)")
        logger.info(f"💾 Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python crawl_formulas_hybrid.py <input_file> [output_file] [method]")
        print("Methods: hybrid (Crawl4AI+Regex+LLM) | regex (Regex+LLM only)")
        print("Example: python crawl_formulas_hybrid.py data/links.json data/formulas.json hybrid")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    method = sys.argv[3] if len(sys.argv) > 3 else "hybrid"
    
    if method not in ["hybrid", "regex"]:
        logger.error("Method must be 'hybrid' or 'regex'")
        sys.exit(1)
    
    # Run async crawler
    asyncio.run(crawl_formulas_hybrid(input_file, output_file, method))


if __name__ == "__main__":
    main()