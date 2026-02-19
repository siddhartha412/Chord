import { EmbedBuilder, Message } from "discord.js";

export default async function ping(message: Message) {
    const sent = await message.reply("Pinging...");
    const latency = sent.createdTimestamp - message.createdTimestamp;
    const apiPing = Math.round(message.client.ws.ping);

    const embed = new EmbedBuilder()
        .setTitle("Pong!")
        .setColor(0x57f287)
        .addFields(
            { name: "Message Latency", value: `\`${latency}ms\``, inline: true },
            { name: "API Ping", value: `\`${apiPing}ms\``, inline: true }
        );

    await sent.edit({ content: "", embeds: [embed] });
}
