import axios from "axios";
import {
    joinVoiceChannel,
    createAudioPlayer,
    createAudioResource,
    AudioPlayerStatus,
    VoiceConnectionStatus,
    entersState,
    StreamType,
    getVoiceConnection
} from "@discordjs/voice";

import {
    ComponentType,
    Message,
    MessageFlags
} from "discord.js";
import { loadImage } from "@napi-rs/canvas";
import prism from "prism-media";
import { buildNowPlayingPayload } from "./nowPlayingPayload";
import {
    players,
    connections,
    queues,
    nowPlaying,
    musicTextChannels,
    QueueTrack,
    stayInVoice,
    stayInVoiceChannelIds
} from "./playerState";
import { removeStay247 } from "./stay247State";

const DEBUG_MUSIC = process.env.MUSIC_DEBUG === "true";

function debugLog(...args: unknown[]) {
    if (DEBUG_MUSIC) console.log(...args);
}

async function startNextTrack(guildId: string) {
    const player = players.get(guildId);
    const connection = connections.get(guildId) ?? getVoiceConnection(guildId);
    const queue = queues.get(guildId) ?? [];
    const channel = musicTextChannels.get(guildId);

    if (!player || !connection) return false;
    if (!queue.length) {
        nowPlaying.delete(guildId);
        return false;
    }

    const track = queue.shift()!;
    queues.set(guildId, queue);
    nowPlaying.set(guildId, track);

    const stream = new prism.FFmpeg({
        args: [
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", track.url,
            "-analyzeduration", "0",
            "-loglevel", "0",
            "-f", "s16le",
            "-ar", "48000",
            "-ac", "2"
        ]
    });

    debugLog("FFmpeg args:", stream.process.spawnargs);

    stream.on("error", (err) => {
        console.error("FFmpeg stream error:", err);
    });

    const resource = createAudioResource(stream, {
        inputType: StreamType.Raw
    });

    debugLog("Resource created. Readable:", resource.readable, "Started:", resource.started);

    player.play(resource);

    let startedAt = Date.now();
    let pausedAt: number | null = null;
    let pausedMs = 0;

    const getElapsedSeconds = () => {
        const now = pausedAt ?? Date.now();
        const elapsed = Math.floor((now - startedAt - pausedMs) / 1000);
        return Math.max(0, Math.min(track.duration || 0, elapsed));
    };

    const artwork = await loadImage(track.thumbnail).catch(() => null);

    const buildPayload = async (isPaused: boolean) => {
        return buildNowPlayingPayload(track, getElapsedSeconds(), isPaused, artwork);
    };

    if (!channel || !("send" in channel)) return true;

    const response = await channel.send(await buildPayload(false));

    const collector = response.createMessageComponentCollector({
        componentType: ComponentType.Button,
        time: track.duration * 1000 || 300000
    });

    const progressTicker = setInterval(async () => {
        if (player.state.status === AudioPlayerStatus.Idle) return;
        try {
            const isPaused = player.state.status === AudioPlayerStatus.Paused;
            await response.edit(await buildPayload(isPaused));
        } catch {
            // Ignore missing/deleted message errors.
        }
    }, 5000);

    collector.on("collect", async (i) => {
        try {
            if (i.user.id !== track.requestedById) {
                await i.reply({ content: "Only the requester can control this song.", flags: MessageFlags.Ephemeral });
                return;
            }

            if (i.customId === "pause_resume") {
                await i.deferUpdate();
                const isPaused = player.state.status === AudioPlayerStatus.Paused;
                if (isPaused) {
                    if (pausedAt) {
                        pausedMs += Date.now() - pausedAt;
                        pausedAt = null;
                    }
                    player.unpause();
                    await response.edit(await buildPayload(false));
                } else {
                    pausedAt = Date.now();
                    player.pause(true);
                    await response.edit(await buildPayload(true));
                }
            } else if (i.customId === "skip") {
                player.stop();
                await i.reply({ content: "Skipped the song!", flags: MessageFlags.Ephemeral });
                collector.stop();
            } else if (i.customId === "stop") {
                const conn = getVoiceConnection(guildId);
                conn?.destroy();
                connections.delete(guildId);
                players.delete(guildId);
                queues.delete(guildId);
                nowPlaying.delete(guildId);
                stayInVoice.delete(guildId);
                stayInVoiceChannelIds.delete(guildId);
                await removeStay247(guildId);
                await i.reply({ content: "Stopped and left!", flags: MessageFlags.Ephemeral });
                collector.stop();
            }
        } catch (error: any) {
            if (error?.code === 10062) {
                debugLog("Interaction expired before response (10062), ignoring.");
                return;
            }
            console.error("Interaction handler error:", error);
        }
    });

    collector.on("end", () => {
        clearInterval(progressTicker);
        response.delete().catch(() => {});
    });

    return true;
}

export default async function play(message: Message, args: string[]) {
    const voiceChannel = message.member?.voice.channel;

    if (!voiceChannel) {
        await message.reply("Join a voice channel first");
        return;
    }

    if (!args.length) {
        await message.reply("Provide song name");
        return;
    }

    const guildId = message.guild!.id;
    const query = args.join(" ");

    try {
        const res = await axios.get(
            `${process.env.MUSIC_API_URL}/search/songs?query=${encodeURIComponent(query)}`
        );

        const results = res.data.data.results;

        if (!results.length) {
            await message.reply("No songs found");
            return;
        }

        results.sort((a: any, b: any) => (b.playCount || 0) - (a.playCount || 0));

        const song = results[0];
        const downloadUrlObj = song.downloadUrl.find((u: any) => u.quality === "320kbps") || song.downloadUrl[song.downloadUrl.length - 1];

        const track: QueueTrack = {
            title: song.name,
            artist: song.artists.primary.map((a: any) => a.name).join(", ") || "Unknown Artist",
            duration: song.duration,
            thumbnail: song.image[song.image.length - 1].url,
            url: downloadUrlObj.url,
            requestedById: message.author.id
        };

        debugLog("Queued:", track.title, track.artist);
        debugLog("URL:", track.url);

        let connection = connections.get(guildId) ?? getVoiceConnection(guildId);
        if (!connection) {
            connection = joinVoiceChannel({
                channelId: voiceChannel.id,
                guildId,
                adapterCreator: message.guild!.voiceAdapterCreator
            });

            connection.on("stateChange", (oldState, newState) => {
                if (oldState.status !== newState.status) {
                    debugLog(`Connection transitioned from ${oldState.status} to ${newState.status}`);
                }
            });

            connection.on("error", (error) => {
                console.error("Connection error:", error);
            });

            await entersState(connection, VoiceConnectionStatus.Ready, 20000);
            connections.set(guildId, connection);
        }

        let player = players.get(guildId);
        if (!player) {
            player = createAudioPlayer();
            players.set(guildId, player);

            player.on("stateChange", (oldState, newState) => {
                if (oldState.status !== newState.status) {
                    debugLog(`Audio player transitioned from ${oldState.status} to ${newState.status}`);
                }
            });

            player.on(AudioPlayerStatus.Idle, async () => {
                nowPlaying.delete(guildId);
                const started = await startNextTrack(guildId);
                if (!started) {
                    if (!stayInVoice.has(guildId)) {
                        const conn = getVoiceConnection(guildId);
                        conn?.destroy();
                        connections.delete(guildId);
                    }
                    // Keep no active player object while idle to reduce overhead.
                    players.delete(guildId);
                    queues.delete(guildId);
                }
            });

            player.on("error", (err) => {
                console.error("Player error:", err);
                console.error("Detailed error:", JSON.stringify(err, null, 2));
            });
        }

        const subscription = connection.subscribe(player);
        if (subscription) {
            debugLog("Subscribed to player");
        } else {
            console.error("Failed to subscribe to player");
        }

        musicTextChannels.set(guildId, message.channel);

        const guildQueue = queues.get(guildId) ?? [];
        guildQueue.push(track);
        queues.set(guildId, guildQueue);

        if (nowPlaying.has(guildId)) {
            await message.reply(`Added to queue: **${track.title}** - ${track.artist}`);
            message.delete().catch(() => {});
            return;
        }

        await startNextTrack(guildId);
        message.delete().catch(() => {});
    } catch (err) {
        console.error("Playback error:", err);
        await message.reply("Playback failed");
    }
}
