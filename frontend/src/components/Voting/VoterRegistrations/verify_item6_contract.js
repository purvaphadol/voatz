const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'VoterRegistrations.js');
const apiPath = path.join(__dirname, '../../../services/api.js');

const code = fs.readFileSync(filePath, 'utf8');
const apiCode = fs.readFileSync(apiPath, 'utf8');

console.log('=== ITEM 6 VERIFICATION CONTRACT ===');

// Check 1: useDeleteWithDependencies import removed
const hasUseDelete = code.includes('useDeleteWithDependencies');
console.log(`Check 1: useDeleteWithDependencies present in VoterRegistrations.js? ${hasUseDelete} (Expected: false)`);

// Check 2: handleDelete function definition removed
const hasHandleDelete = code.includes('handleDelete');
console.log(`Check 2: handleDelete present in VoterRegistrations.js? ${hasHandleDelete} (Expected: false)`);

// Check 3: Delete icon / GridActionsCellItem for delete removed
const hasDeleteAction = code.includes("label=\"Delete\"") || code.includes("key=\"delete\"");
console.log(`Check 3: Delete GridActionsCellItem present in VoterRegistrations.js? ${hasDeleteAction} (Expected: false)`);

// Check 4: voterRegistrationsAPI has no delete method
const hasApiDelete = apiCode.includes('voterRegistrationsAPI') && apiCode.substring(apiCode.indexOf('voterRegistrationsAPI')).includes('delete:');
console.log(`Check 4: voterRegistrationsAPI.delete defined in api.js? ${hasApiDelete} (Expected: false)`);

if (!hasUseDelete && !hasHandleDelete && !hasDeleteAction && !hasApiDelete) {
  console.log('\nSUCCESS: All Item 6 frontend contract checks passed cleanly!');
} else {
  console.error('\nFAILURE: Item 6 checks failed.');
  process.exit(1);
}
