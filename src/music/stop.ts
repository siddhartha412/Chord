
import { Message } from "discord.js";
import { getVoiceConnection } from "@discordjs/voice";
import { connections, musicTextChannels, nowPlaying, players, queues, stayInVoice, stayInVoiceChannelIds } from "./playerState";
import { removeStay247 } from "./stay247State";

export default async function stop(message: Message) {
    const voiceChannel = message.member?.voice.channel;
    if (!voiceChannel) {
        await message.reply("You need to be in a voice channel to stop music.");
        return;
    }

    const connection = getVoiceConnection(message.guild!.id);

    if (connection) {
        connection.destroy();
        connections.delete(message.guild!.id);
        players.delete(message.guild!.id);
        queues.delete(message.guild!.id);
        nowPlaying.delete(message.guild!.id);
        musicTextChannels.delete(message.guild!.id);
        stayInVoice.delete(message.guild!.id);
        stayInVoiceChannelIds.delete(message.guild!.id);
        await removeStay247(message.guild!.id);
        await message.reply("Stopped playback and left the voice channel.");
    } else {
        await message.reply("I'm not playing anything.");
    }
}
