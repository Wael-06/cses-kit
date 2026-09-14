const readline = require("readline");

const lines = [];
const input = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

input.on("line", (line) => lines.push(line));
input.on("close", () => {
  const values = lines.join("\n").trim().split(/\s+/);

  // your solution goes here
  void values;
});
