import * as dotenv from "dotenv";
dotenv.config();

import {
  Client,
  GatewayIntentBits,
  Message
} from "discord.js";
import {
  joinVoiceChannel,
  VoiceConnectionStatus,
  entersState
} from "@discordjs/voice";

import { connections, stayInVoice, stayInVoiceChannelIds } from "./music/playerState";
import { readStay247State } from "./music/stay247State";

const token = process.env.DISCORD_TOKEN!;

const prefix = ";";
const ownerId = "1261577588669939755";

type MessageHandler = (message: Message, args: string[]) => Promise<void>;

type CommandRegistry = {
  play: MessageHandler;
  stop: MessageHandler;
  skip: MessageHandler;
  ping: MessageHandler;
  queue: MessageHandler;
  twentyfourseven: MessageHandler;
};

let commands: CommandRegistry;

function loadCommands() {
  const modules = [
    "./music/play",
    "./music/stop",
    "./music/skip",
    "./ping",
    "./music/queue",
    "./music/twentyfourseven"
  ] as const;

  for (const mod of modules) {
    delete require.cache[require.resolve(mod)];
  }

  commands = {
    play: require("./music/play").default,
    stop: require("./music/stop").default,
    skip: require("./music/skip").default,
    ping: require("./ping").default,
    queue: require("./music/queue").default,
    twentyfourseven: require("./music/twentyfourseven").default
  };
}

loadCommands();

const client = new Client({

  intents: [

    GatewayIntentBits.Guilds,

    GatewayIntentBits.GuildMessages,

    GatewayIntentBits.MessageContent,

    GatewayIntentBits.GuildVoiceStates

  ],

  presence: {
    status: "idle"
  }

});

client.once("clientReady", async () => {

  console.log(`✅ Bot online as ${client.user?.tag}`);

  const persisted = await readStay247State();

  for (const [guildId, channelId] of Object.entries(persisted)) {
    try {
      const guild = client.guilds.cache.get(guildId) ?? await client.guilds.fetch(guildId);
      const channel = guild.channels.cache.get(channelId) ?? await guild.channels.fetch(channelId);

      if (!channel || !("isVoiceBased" in channel) || !channel.isVoiceBased()) {
        continue;
      }

      const connection = joinVoiceChannel({
        channelId: channel.id,
        guildId,
        adapterCreator: guild.voiceAdapterCreator
      });

      await entersState(connection, VoiceConnectionStatus.Ready, 20000);
      connections.set(guildId, connection);
      stayInVoice.add(guildId);
      stayInVoiceChannelIds.set(guildId, channel.id);

      console.log(`🔁 Rejoined 24/7 VC in guild ${guildId}`);
    } catch (err) {
      console.error(`Failed to restore 24/7 in guild ${guildId}:`, err);
    }
  }

});

client.on("messageCreate", async (message: Message) => {

  if (message.author.bot) return;

  if (!message.content.startsWith(prefix)) return;

  const args =
    message.content.slice(prefix.length).trim().split(" ");

  const command = args.shift()?.toLowerCase();

  if (command === "play") {

    await commands.play(message, args);

  } else if (command === "stop") {

    await commands.stop(message, args);

  } else if (command === "skip") {

    await commands.skip(message, args);

  } else if (command === "ping") {

    await commands.ping(message, args);

  } else if (command === "queue") {

    await commands.queue(message, args);

  } else if (command === "24/7" || command === "247") {

    await commands.twentyfourseven(message, args);

  } else if (command === "reload") {

    if (message.author.id !== ownerId) {
      await message.reply("Owner only command.");
      return;
    }

    try {
      loadCommands();
      await message.reply("Reloaded commands.");
    } catch (err) {
      console.error("Reload failed:", err);
      await message.reply("Reload failed.");
    }

  } else if (command === "restart") {

    if (message.author.id !== ownerId) {
      await message.reply("Owner only command.");
      return;
    }

    await message.reply("Restarting bot process...");
    setTimeout(() => process.exit(0), 500);

  }

});

client.login(token);
