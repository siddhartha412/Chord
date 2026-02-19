import {
    AttachmentBuilder,
    ActionRowBuilder,
    ButtonBuilder,
    ButtonStyle,
    MessageFlags
} from "discord.js";
import {
    ContainerBuilder,
    MediaGalleryBuilder,
    MediaGalleryItemBuilder,
    TextDisplayBuilder
} from "@discordjs/builders";
import { Image } from "@napi-rs/canvas";
import { QueueTrack } from "./playerState";
import { renderNowPlayingCard } from "./nowPlayingCard";

export async function buildNowPlayingPayload(
    track: QueueTrack,
    elapsedSeconds: number,
    isPaused: boolean,
    artwork: Image | null
) {
    const imageBuffer = renderNowPlayingCard(track, elapsedSeconds, artwork);
    const attachment = new AttachmentBuilder(imageBuffer, { name: "now-playing.png" });
    const primaryArtist = track.artist.split(",")[0]?.trim() || track.artist;

    const container = new ContainerBuilder()
        .setAccentColor(0x2f3136)
        .addTextDisplayComponents(
            new TextDisplayBuilder().setContent("Now Playing")
        )
        .addMediaGalleryComponents(
            new MediaGalleryBuilder().addItems(
                new MediaGalleryItemBuilder()
                    .setURL("attachment://now-playing.png")
                    .setDescription(`${track.title} - ${primaryArtist}`)
            )
        )
        .addActionRowComponents(
            new ActionRowBuilder<ButtonBuilder>().addComponents(
                new ButtonBuilder()
                    .setCustomId("pause_resume")
                    .setLabel(isPaused ? "Resume" : "Pause")
                    .setEmoji("⏯")
                    .setStyle(ButtonStyle.Secondary),
                new ButtonBuilder()
                    .setCustomId("skip")
                    .setLabel("Skip")
                    .setEmoji("⏭")
                    .setStyle(ButtonStyle.Primary),
                new ButtonBuilder()
                    .setCustomId("stop")
                    .setLabel("Stop")
                    .setEmoji("⏹")
                    .setStyle(ButtonStyle.Danger)
            )
        );

    return {
        flags: MessageFlags.IsComponentsV2 as const,
        files: [attachment],
        components: [container]
    };
}
