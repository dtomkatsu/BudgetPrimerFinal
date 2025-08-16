import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from budgetprimer.parsers.fast_parser import FastBudgetParser

def test_trn597_parsing():
    # Create a test file with just the TRN597 section
    test_content = """
    32. TRN597 - HIGHWAYS SAFETY
    OPERATING                  TRN     12,319,296B 12,319,296B
    TRN     6,495,670N  6,495,670N
    
    TRN     1,214,379P  1,214,379P
    33. TRN995 - GENERAL ADMINISTRATION
    """
    
    # Write to a temporary file
    test_file = "/tmp/test_trn597.txt"
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    # Parse the test file
    parser = FastBudgetParser()
    allocations = parser.parse(test_file)
    
    # Filter for TRN597 allocations
    trn597_allocations = [a for a in allocations if a.program_id == 'TRN597']
    
    print(f"Found {len(trn597_allocations)} allocations for TRN597")
    for alloc in trn597_allocations:
        print(f"- Amount: ${alloc.amount:,.2f}, Fund: {alloc.fund_type}, Section: {alloc.section}")
    
    # Check if the 1,214,379P amount is correctly assigned to TRN597
    p_fund_alloc = [a for a in trn597_allocations if a.fund_type == 'P']
    if p_fund_alloc:
        print(f"✅ Found P fund allocation: ${p_fund_alloc[0].amount:,.2f} for TRN597")
    else:
        print("❌ Did not find P fund allocation for TRN597")
    
    # Clean up
    os.remove(test_file)

if __name__ == "__main__":
    test_trn597_parsing()
