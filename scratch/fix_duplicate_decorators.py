import re

with open('backend/api/enterprise.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and remove consecutive duplicate route decorators
# Pattern: @router.get("/foo")\n@router.get("/foo")  -> @router.get("/foo")
pattern = r'(@router\.(?:get|post|put|delete)\("[^"]+"\))\n\1'
fixed = re.sub(pattern, r'\1', content)

removed = content.count('\n') - fixed.count('\n')
print(f'Removed {removed} duplicate decorator lines')

with open('backend/api/enterprise.py', 'w', encoding='utf-8') as f:
    f.write(fixed)

print('Done')
