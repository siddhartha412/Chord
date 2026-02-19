import { Message } from "discord.js";
import { nowPlaying, queues } from "./playerState";

function formatDuration(sec: number) {
    const total = Number.isFinite(sec) && sec > 0 ? sec : 0;
    const m = Math.floor(total / 60);
    const s = Math.floor(total % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
}

export default async function queue(message: Message) {
    const guildId = message.guild!.id;
    const current = nowPlaying.get(guildId);
    const upcoming = queues.get(guildId) ?? [];

    if (!current && upcoming.length === 0) {
        await message.reply("Queue is empty.");
        return;
    }

    const lines: string[] = [];

    if (current) {
        lines.push(`Now Playing: **${current.title}** - ${current.artist} (${formatDuration(current.duration)})`);
    }

    if (upcoming.length > 0) {
        lines.push("");
        lines.push("Up Next:");
        for (let i = 0; i < Math.min(upcoming.length, 10); i++) {
            const track = upcoming[i];
            lines.push(`${i + 1}. **${track.title}** - ${track.artist} (${formatDuration(track.duration)})`);
        }
        if (upcoming.length > 10) {
            lines.push(`...and ${upcoming.length - 10} more`);
        }
    }

    await message.reply(lines.join("\n"));
}
