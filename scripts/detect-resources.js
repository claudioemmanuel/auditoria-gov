const os = require('os');
const fs = require('fs');
const path = require('path');

// Detect resources
const cpuCores = os.cpus().length;
const totalMemMb = Math.round(os.totalmem() / 1024 / 1024);

// Profile detection
let profile = 'low';
if (process.env.MACHINE_PROFILE) {
  profile = process.env.MACHINE_PROFILE;
} else if (totalMemMb > 8192) {
  profile = 'high';
} else if (totalMemMb >= 4096) {
  profile = 'medium';
}

const envFile = path.join(__dirname, `../env/${profile}.env`);
const envOut = path.join(__dirname, '../.env.runtime');

if (!fs.existsSync(envFile)) {
  console.error(`Profile env file not found: ${envFile}`);
  process.exit(1);
}

const envVars = fs.readFileSync(envFile, 'utf-8');
const meta = [
  `CPU_CORES=${cpuCores}`,
  `TOTAL_MEM_MB=${totalMemMb}`,
  `MACHINE_PROFILE=${profile}`
];

fs.writeFileSync(envOut, envVars + '\n' + meta.join('\n') + '\n');
console.log(`Profile: ${profile}`);
console.log(`.env.runtime generated with CPU: ${cpuCores}, MEM: ${totalMemMb}MB`);
