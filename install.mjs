#!/usr/bin/env node
// 技能安装器：把本仓库 skills/ 下的技能复制到 WorkBuddy 的 skills 目录。
// 通过 npx github:user/repo 运行时，本文件即 bin 入口。
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILLS_SRC = path.join(__dirname, 'skills');

function parseArgs(argv) {
  const a = { target: null, project: false, dryRun: false, force: true, list: false, help: false };
  for (let i = 2; i < argv.length; i++) {
    const x = argv[i];
    if (x === '--target' || x === '-t') a.target = argv[++i];
    else if (x === '--project' || x === '-p') a.project = true;
    else if (x === '--dry-run') a.dryRun = true;
    else if (x === '--no-force') a.force = false;
    else if (x === '--list' || x === '-l') a.list = true;
    else if (x === '--help' || x === '-h') a.help = true;
  }
  return a;
}

function defaultTarget(project) {
  if (project) return path.join(process.cwd(), '.workbuddy', 'skills');
  return path.join(os.homedir(), '.workbuddy', 'skills'); // 用户级，跨项目生效
}

function listSkills(src) {
  if (!fs.existsSync(src)) return [];
  return fs.readdirSync(src, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);
}

function printHelp() {
  console.log(`技能安装器

用法:
  npx github:yourname/skills-library        # 安装到用户级 skills 目录
  node install.mjs [选项]

选项:
  -t, --target <dir>   指定目标目录（覆盖默认）
  -p, --project        安装到当前项目的 .workbuddy/skills
      --dry-run        只打印将要执行的操作，不写文件
      --no-force       已存在的技能跳过（默认覆盖）
  -l, --list           列出 skills/ 下所有可用技能
  -h, --help           显示帮助
`);
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) return printHelp();

  if (!fs.existsSync(SKILLS_SRC)) {
    console.error('未找到 skills/ 目录: ' + SKILLS_SRC);
    process.exit(1);
  }
  const skills = listSkills(SKILLS_SRC);
  if (skills.length === 0) {
    console.error('skills/ 目录下没有任何技能文件夹。');
    process.exit(1);
  }

  if (args.list) {
    console.log('可用技能:');
    skills.forEach(s => console.log('  - ' + s));
    return;
  }

  const target = args.target ? path.resolve(args.target) : defaultTarget(args.project);
  console.log('源目录  : ' + SKILLS_SRC);
  console.log('目标目录: ' + target + (args.dryRun ? '  (dry-run)' : ''));
  console.log('---');

  let copied = 0, skipped = 0;
  for (const name of skills) {
    const src = path.join(SKILLS_SRC, name);
    const dest = path.join(target, name);
    if (fs.existsSync(dest) && !args.force) {
      console.log(`跳过 ${name}（已存在，用 --force 覆盖）`);
      skipped++;
      continue;
    }
    if (!args.dryRun) fs.cpSync(src, dest, { recursive: true, force: true });
    console.log(`${args.dryRun ? '[模拟] ' : ''}安装 ${name}`);
    copied++;
  }

  console.log('---');
  if (args.dryRun) {
    console.log(`将安装 ${copied} 个技能到 ${target}`);
  } else {
    console.log(`已安装 ${copied} 个技能到 ${target}`);
    if (skipped) console.log(`跳过 ${skipped} 个（已存在）`);
    console.log('提示: 安装后请重启 WorkBuddy（或刷新 Skill 列表），即可在对话中调用这些技能。');
  }
}

main();
