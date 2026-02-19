
import { Message } from "discord.js";
import { players } from "./playerState";

export default async function skip(message: Message) {
    const voiceChannel = message.member?.voice.channel;
    if (!voiceChannel) {
        await message.reply("You need to be in a voice channel to skip music.");
        return;
    }

    const player = players.get(message.guild!.id);

    if (player) {
        player.stop();
        await message.reply("Skipped current song.");
    } else {
        await message.reply("No songs are currently playing.");
    }
}
