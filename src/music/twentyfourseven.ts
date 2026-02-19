import {
    joinVoiceChannel,
    VoiceConnectionStatus,
    entersState,
    getVoiceConnection
} from "@discordjs/voice";
import { Message } from "discord.js";
import { connections, nowPlaying, players, queues, stayInVoice, stayInVoiceChannelIds } from "./playerState";
import { removeStay247, setStay247 } from "./stay247State";

export default async function twentyFourSeven(message: Message, args: string[]) {
    const guildId = message.guild?.id;
    if (!guildId) return;

    const current = stayInVoice.has(guildId);
    const option = args[0]?.toLowerCase();

    const shouldEnable =
        option === "on" || option === "enable" || option === "true"
            ? true
            : option === "off" || option === "disable" || option === "false"
              ? false
              : !current;

    if (shouldEnable) {
        const voiceChannel = message.member?.voice.channel;
        if (!voiceChannel) {
            await message.reply("Join a voice channel first to enable 24/7 mode.");
            return;
        }

        let connection = connections.get(guildId) ?? getVoiceConnection(guildId);
        if (!connection) {
            connection = joinVoiceChannel({
                channelId: voiceChannel.id,
                guildId,
                adapterCreator: message.guild!.voiceAdapterCreator
            });

            await entersState(connection, VoiceConnectionStatus.Ready, 20000);
            connections.set(guildId, connection);
        }

        stayInVoice.add(guildId);
        stayInVoiceChannelIds.set(guildId, voiceChannel.id);
        await setStay247(guildId, voiceChannel.id);
        await message.reply("24/7 mode enabled. I will stay in VC when idle.");
        return;
    }

    stayInVoice.delete(guildId);
    stayInVoiceChannelIds.delete(guildId);
    await removeStay247(guildId);

    const connection = connections.get(guildId) ?? getVoiceConnection(guildId);
    const hasQueue = (queues.get(guildId)?.length ?? 0) > 0;
    const hasNowPlaying = nowPlaying.has(guildId);

    if (connection && !hasQueue && !hasNowPlaying) {
        connection.destroy();
        connections.delete(guildId);
        players.delete(guildId);
        queues.delete(guildId);
    }

    await message.reply("24/7 mode disabled.");
}
