import { promises as fs } from "node:fs";
import { dirname, join } from "node:path";

const statePath = join(process.cwd(), "data", "stay247.json");

type Stay247State = Record<string, string>;

async function ensureDir() {
    await fs.mkdir(dirname(statePath), { recursive: true });
}

export async function readStay247State(): Promise<Stay247State> {
    try {
        const raw = await fs.readFile(statePath, "utf8");
        const parsed = JSON.parse(raw) as Stay247State;
        if (!parsed || typeof parsed !== "object") return {};
        return parsed;
    } catch {
        return {};
    }
}

async function writeState(state: Stay247State) {
    await ensureDir();
    await fs.writeFile(statePath, JSON.stringify(state, null, 2), "utf8");
}

export async function setStay247(guildId: string, channelId: string) {
    const state = await readStay247State();
    state[guildId] = channelId;
    await writeState(state);
}

export async function removeStay247(guildId: string) {
    const state = await readStay247State();
    delete state[guildId];
    await writeState(state);
}
