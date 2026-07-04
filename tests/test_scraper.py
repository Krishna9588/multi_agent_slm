from agents.web_scraper import web_scraper

# print("Test 1: python.org/about (static page - urllib should work)")
# r = web_scraper("https://www.python.org/about/")
# print(f"  strategy  : {r['strategy']}")
# print(f"  word_count: {r['word_count']}")
# print(f"  attempts  : {r['attempts']}")
# print(f"  title     : {r['title']}")
# print()
#
# print("Test 2: Force requests+BS4 strategy")
# r2 = web_scraper("https://www.python.org/about/", strategy="requests")
# print(f"  strategy  : {r2['strategy']}")
# print(f"  word_count: {r2['word_count']}")
# print(f"  text[0:120]: {r2['text'][:120]}")
# print()

print("Test 3: Force parsel (XPath) strategy")
r3 = web_scraper("https://www.python.org/about/", strategy="parsel")
print(f"  strategy  : {r3['strategy']}")
print(f"  attempts  : {r3['attempts']}")
print(f"  word_count: {r3['word_count']}")
print(f"  title     : {r3['title']}")
print()

print("Test 4: JS-heavy page - auto cascade (proplusdata.co)")
r4 = web_scraper("https://proplusdata.co", strategy="auto")
print(f"  strategy  : {r4['strategy']}")
print(f"  word_count: {r4['word_count']}")
print(f"  attempts  : {r4['attempts']}")
print(f"  title     : {r4['title']}")

print(f"  title     : {r4['text']}")
print()

print("All tests complete!")
