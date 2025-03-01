#!/usr/bin/env -S deno run --allow-env --allow-all

// https://docs.deno.com/examples/hashbang_tutorial/
// chmod +x printenv.ts
// ./printenv.ts
// const path = Deno.env.get("DENO_INSTALL_ROOT");
// const path = Deno.env.get("PATH");

// take a command argument. if no command is given, print all environment variables
const args = process.argv;

// process.argv[0] is the path to the deno executable
// process.argv[1] is the path to the script
console.log(`args=${args}`);

if (args.length === 1) {
    // print all environment variables
    
    
} else {
    // if the command is not found, print an error message
    const key = args[2];
    const value = process.env[key];
    console.log(`${key}=${value}`);
}
