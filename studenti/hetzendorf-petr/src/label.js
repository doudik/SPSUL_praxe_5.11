const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline/promises');
const { stdin, stdout } = require('node:process');

const args = process.argv.slice(2);
const editId = args.length === 4 && args[2] === '--edit' && /^[1-9]\d*$/.test(args[3])
  ? Number(args[3]) : null;
if ((args.length !== 2 && !(args.length === 4 && Number.isSafeInteger(editId))) ||
    args[0] !== '--split' || !['dev', 'test'].includes(args[1])) {
  console.error('Použití: node src/label.js --split dev|test [--edit ID]');
  process.exitCode = 1;
} else {
  main(args[1], editId).catch((error) => {
    console.error('Označování se nezdařilo:', error.message);
    process.exitCode = 1;
  });
}

async function main(split, editId) {
  const file = path.join(__dirname, '..', 'data', `${split}.jsonl`);
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).filter((line) => line.trim());
  const cases = lines.map((line, index) => {
    try {
      return JSON.parse(line);
    } catch {
      throw new Error(`Neplatný JSON na řádku ${index + 1} v ${file}.`);
    }
  });

  if (editId !== null && !cases.some((item) => item.id === editId)) {
    throw new Error(`Případ s ID ${editId} v sadě ${split} neexistuje.`);
  }

  const rl = readline.createInterface({ input: stdin, output: stdout });
  const pizzas = ['margherita', 'salamova', 'hawai', 'quattro formaggi'];

  async function askYesNo(question) {
    while (true) {
      const answer = (await rl.question(question)).trim().toLowerCase();
      if (['a', 'ano'].includes(answer)) return true;
      if (['n', 'ne'].includes(answer)) return false;
      console.log('Zadejte ano (a) nebo ne (n).');
    }
  }

  async function askCount(name) {
    while (true) {
      const answer = (await rl.question(`Počet (${name}; kladné celé číslo nebo null): `)).trim();
      if (answer.toLowerCase() === 'null') return null;
      const count = Number(answer);
      if (/^[0-9]+$/.test(answer) && Number.isSafeInteger(count) && count > 0) return count;
      console.log('Zadejte kladné celé číslo nebo null.');
    }
  }

  async function askPayment() {
    while (true) {
      const answer = (await rl.question('Platba (hotovost, karta nebo null): ')).trim().toLowerCase();
      if (answer === 'null') return null;
      if (answer === 'hotovost' || answer === 'karta') return answer;
      console.log('Zadejte hotovost, karta nebo null.');
    }
  }

  try {
    for (const item of cases) {
      if (editId !== null ? item.id !== editId : item.expected != null) continue;

      console.log(`\nID: ${item.id}\nVstup: ${item.input}`);
      let confirmed = false;
      while (!confirmed) {
        const polozky = [];
        for (const nazev of pizzas) {
          if (await askYesNo(`Je objednána pizza ${nazev}? (a/n): `)) {
            polozky.push({ nazev, pocet: await askCount(nazev) });
          }
        }
        const address = (await rl.question('Adresa (prázdná odpověď nebo null znamená null): ')).trim();
        const expected = { polozky, adresa: !address || address.toLowerCase() === 'null' ? null : address, platba: await askPayment() };
        console.log('\nExpected:');
        console.log(JSON.stringify(expected, null, 2));
        confirmed = await askYesNo('Uložit tento výsledek? (a/n): ');
        if (confirmed) {
          item.expected = expected;
          const temporaryFile = `${file}.${process.pid}.tmp`;
          let temporaryFileCreated = false;
          try {
            fs.writeFileSync(temporaryFile, `${cases.map((entry) => JSON.stringify(entry)).join('\n')}\n`, { encoding: 'utf8', flag: 'wx' });
            temporaryFileCreated = true;
            fs.renameSync(temporaryFile, file);
          } finally {
            if (temporaryFileCreated && fs.existsSync(temporaryFile)) fs.unlinkSync(temporaryFile);
          }
          console.log('Uloženo.');
        } else {
          console.log('Výsledek nebyl uložen. Zadejte případ znovu.');
        }
      }
    }
    console.log(editId === null ? '\nVšechny případy v této sadě jsou vyplněné.' : '\nÚprava případu je dokončena.');
  } finally {
    rl.close();
  }
}
