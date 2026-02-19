
import { createAudioPlayer, VoiceConnection } from "@discordjs/voice";
import { Message } from "discord.js";

export const players = new Map<string, ReturnType<typeof createAudioPlayer>>();
export const connections = new Map<string, VoiceConnection>();

export type QueueTrack = {
    title: string;
    artist: string;
    duration: number;
    thumbnail: string;
    url: string;
    requestedById: string;
};

export const queues = new Map<string, QueueTrack[]>();
export const nowPlaying = new Map<string, QueueTrack>();
export const musicTextChannels = new Map<string, Message["channel"]>();
export const stayInVoice = new Set<string>();
export const stayInVoiceChannelIds = new Map<string, string>();
