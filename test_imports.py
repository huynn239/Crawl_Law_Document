"""Test imports sau khi restructure"""

print("Testing imports...")

try:
    # Core modules
    from core.extractors.production_extractor import ProductionReadyExtractor
    print("✓ core.extractors.production_extractor")
except Exception as e:
    print(f"✗ core.extractors.production_extractor: {e}")

try:
    from core.patterns.regex_patterns import EnhancedRegexPatterns
    print("✓ core.patterns.regex_patterns")
except Exception as e:
    print(f"✗ core.patterns.regex_patterns: {e}")

try:
    from core.extractors.formula_separator import SmartFormulaSeparator
    print("✓ core.extractors.formula_separator")
except Exception as e:
    print(f"✗ core.extractors.formula_separator: {e}")

try:
    # tvpl_crawler
    from tvpl_crawler.core.config import settings
    print("✓ tvpl_crawler.core.config")
except Exception as e:
    print(f"✗ tvpl_crawler.core.config: {e}")

try:
    from tvpl_crawler.core import db
    print("✓ tvpl_crawler.core.db")
except Exception as e:
    print(f"✗ tvpl_crawler.core.db: {e}")

try:
    # Scripts
    from scripts.extract.adaptive_formula_extractor import AdaptiveFormulaExtractor
    print("✓ scripts.extract.adaptive_formula_extractor")
except Exception as e:
    print(f"✗ scripts.extract.adaptive_formula_extractor: {e}")

print("\n✓ Import test completed!")
