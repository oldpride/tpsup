#!/usr/bin/env -S deno run --allow-env --allow-all

// https://docs.deno.com/examples/hashbang_tutorial/
// chmod +x printenv.ts
// ./printenv.ts
// const path = Deno.env.get("DENO_INSTALL_ROOT");
// const path = Deno.env.get("PATH");

// take a command argument. if no command is given, print all environment variables
const args = Deno.args;
if (args.length === 0) {
    for (const [key, value] of Object.entries(Deno.env.toObject())) {
        console.log(`${key}=${value}`);
    }
} else {
    // if the command is not found, print an error message
    const key = args[0];
    const value = Deno.env.get(key);
    console.log(`${key}=${value}`);
}
