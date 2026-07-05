const fs = require('fs');
const path = require('path');
const glob = require('glob');

const replacements = [
  { regex: /bg-\[#111114\]/g, replace: 'bg-surface' },
  { regex: /bg-\[#09090B\]/g, replace: 'bg-surface' },
  { regex: /bg-\[#18181B\]/g, replace: 'bg-muted' },
  { regex: /bg-\[#27272A\]/g, replace: 'bg-muted' },
  { regex: /bg-\[#DC2626\]/g, replace: 'bg-error' },
  { regex: /bg-\[#22C55E\]/g, replace: 'bg-success' },
  { regex: /bg-\[#F59E0B\]/g, replace: 'bg-primary' },
  { regex: /border-\[#111114\]/g, replace: 'border-muted' },
  { regex: /border-\[#09090B\]/g, replace: 'border-muted' },
  { regex: /border-\[#18181B\]/g, replace: 'border-muted' },
  { regex: /border-\[#27272A\]/g, replace: 'border-muted' },
  { regex: /border-\[#DC2626\]/g, replace: 'border-error' },
  { regex: /border-\[#22C55E\]/g, replace: 'border-success' },
  { regex: /border-\[#F59E0B\]/g, replace: 'border-primary' },
  { regex: /text-\[#EF4444\]/g, replace: 'text-error' },
  { regex: /text-\[#F59E0B\]/g, replace: 'text-primary' },
  { regex: /text-\[#22C55E\]/g, replace: 'text-success' },
];

function replaceInFile(file) {
  const original = fs.readFileSync(file, 'utf8');
  let content = original;
  replacements.forEach(r => {
    content = content.replace(r.regex, r.replace);
  });
  // Add transition and hover utilities if missing
  content = content.replace(/className="([^"]*)"/g, (match, cls) => {
    let newCls = cls;
    if (/bg-/.test(cls) && !/transition-standard/.test(cls)) newCls += ' transition-standard';
    if (/border-/.test(cls) && !/hover:scale-105/.test(cls)) newCls += ' hover:scale-105';
    return `className="${newCls.trim()}"`;
  });
  if (content !== original) {
    fs.writeFileSync(file, content, 'utf8');
    console.log('Updated', file);
  }
}

const pattern = path.join('frontend', 'components', 'dashboard', '**', '*.{tsx,jsx,js,ts}');
const files = glob.sync(pattern, { absolute: true });
files.forEach(replaceInFile);
