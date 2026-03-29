import esbuild from "esbuild";

const watch = process.argv.includes("--watch");

const ctx = await esbuild.context({
  entryPoints: ["src/main.ts"],
  bundle: true,
  outfile: "dist/main.js",
  format: "cjs",
  platform: "node",
  external: ["obsidian", "electron"],
  sourcemap: true,
  logLevel: "info",
});

if (watch) {
  await ctx.watch();
  console.log("Watching for changes...");
} else {
  await ctx.rebuild();
  await ctx.dispose();
}
