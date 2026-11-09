import pkg from '/opt/homebrew/lib/node_modules/ws/index.js'; const { WebSocket } = pkg;
import fs from 'fs';
import path from 'path';

const PAGE_ID = 'BC482062878FB1D6C502D98D26D99AB5';
const WS_URL = `ws://127.0.0.1:9222/devtools/page/${PAGE_ID}`;
const SAVE_DIR = path.join(process.env.HOME, 'workspace/rufus-coffee-research-v2');
if (!fs.existsSync(SAVE_DIR)) fs.mkdirSync(SAVE_DIR, { recursive: true });

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

const ws = new WebSocket(WS_URL);
let msgId = 0;
function send(method, params = {}) {
  return new Promise((res, rej) => {
    const id = ++msgId;
    ws.send(JSON.stringify({ id, method, params }));
    const h = d => { const m = JSON.parse(d); if (m.id === id) { ws.off('message', h); res(m.result); } };
    ws.on('message', h); ws.on('error', rej);
  });
}
async function evalExpr(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  return r?.result?.value || '';
}

const questions = [
  'Someone already owns the CERA+ portable espresso machine — what would make OutIn Nano the better choice for them?',
  'For a camper who needs coffee before a 5am hike, which matters more: heating speed or number of hot shots available?',
  'If someone mostly drinks espresso at their office desk but occasionally goes camping, is OutIn Nano over-engineered compared to a simple capsule machine?',
  'Between self-heating and having a larger battery that can brew more cups, which is the more valued feature for travel espresso users?',
  'Is the 670-gram weight difference between OutIn Nano and CERA+ actually noticeable during a full-day hike, or does it only matter for carry-on luggage?',
  'When buying a portable espresso machine for international travel, how do airline carry-on regulations influence which brand someone chooses?',
  'For a road-trip couple sharing one machine, what is the minimum number of consecutive hot shots before they need to recharge — and which brands meet that threshold?',
  'How important is the NS capsule compatibility compared to ground-coffee-only mode for someone who switches between home and travel?',
  'In what specific car or van life situation would someone choose OutIn Nano over just bringing a manual hand pump espresso maker?',
  'A digital nomad who works from a different city each week — is OutIn Nano\'s self-heating feature actually faster or more convenient than finding a power outlet and using a portable kettle?',
];

async function waitForComplete(maxMs = 40000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const r = await evalExpr(`(function(){return document.body.textContent.includes("Rufus has completed generating a response")?"DONE":"WAITING";})()`);
    if (r === 'DONE') return true;
    await sleep(1500);
  }
  return false;
}

async function askRufus(q, idx) {
  const esc = q.replace(/`/g, '\\`').replace(/\$/g, '\\$');
  
  await evalExpr(`(function(){const ta=document.getElementById("rufus-text-area");if(!ta)return"NF";ta.focus();ta.value="";ta.dispatchEvent(new Event("input",{bubbles:true}));ta.value=\`${esc}\`;ta.dispatchEvent(new Event("input",{bubbles:true}));return"TYPED";})()`);
  await evalExpr(`(function(){document.getElementById("rufus-text-area").dispatchEvent(new KeyboardEvent("keydown",{bubbles:true,cancelable:true,key:"Enter",code:"Enter"}));})()`);
  
  await sleep(8000);
  await waitForComplete(40000);
  await sleep(3000);
  
  const raw = await evalExpr(`(function(){
    const p=document.querySelector(".nav-rufus-content");
    if(!p)return"NO_PANEL";
    const allText=p.innerText||"";
    const marker="${q.substring(0,25).replace(/[?'".,]/g,'')}";
    let start=allText.indexOf(marker);
    if(start===-1)start=Math.max(0,allText.length-15000);
    let end=allText.indexOf("Customer question",start+300);
    if(end===-1||end-start>15000)end=start+13000;
    return allText.substring(start,end).trim();
  })()`);
  
  return raw || 'EMPTY_RESPONSE';
}

async function main() {
  await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
  
  await send('Page.navigate', { url: 'https://www.amazon.com/s?k=portable+espresso+machine&s=review-rank' });
  await sleep(8000);
  
  const ta = await evalExpr(`document.getElementById("rufus-text-area")?"READY":"NOT_READY"`);
  console.log('Rufus ready:', ta);
  
  const results = [];
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i];
    process.stdout.write(`Q${i+1}/10: ${q.substring(0,50)}... `);
    
    const raw = await askRufus(q, i);
    
    const lines = raw.split('\n').filter(l=>l.trim().length>10&&l.trim().length<150);
    const fuMarkers = ['Show ','Best ','How to ','What ','How much ','Tips for ','Compare ','Which ','Can you '];
    const followUps = [...new Set(lines.filter(l=>fuMarkers.some(m=>l.trim().startsWith(m))))].slice(0,5);
    
    results.push({ q, raw, followUps });
    
    fs.writeFileSync(path.join(SAVE_DIR, `Q${i+1}.md`),
      `# Q${i+1}\n## Question\n${q}\n\n## Rufus Answer\n${raw}\n\n## Follow-up Suggestions\n${followUps.map(f=>'- '+f.trim()).join('\n') || 'None'}\n`, 'utf8');
    
    process.stdout.write(`${raw.length} chars\n`);
    await sleep(4000);
  }
  
  fs.writeFileSync(path.join(SAVE_DIR, 'summary.json'), JSON.stringify(results, null, 2), 'utf8');
  
  // Print all answers
  for (let i = 0; i < results.length; i++) {
    console.log(`\n\n${'='.repeat(80)}\nQ${i+1}: ${questions[i]}\n${'='.repeat(80)}\n${results[i].raw}\n`);
  }
  
  console.log('\nAll saved to', SAVE_DIR);
  ws.close();
  process.exit(0);
}

main().catch(e => { console.error(e); process.exit(1); });
