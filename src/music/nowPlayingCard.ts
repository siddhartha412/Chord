import { createCanvas, GlobalFonts, Image } from "@napi-rs/canvas";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { QueueTrack } from "./playerState";

const MONTSERRAT_VARIABLE = join(process.cwd(), "assets/fonts/Montserrat-VariableFont_wght.ttf");

if (existsSync(MONTSERRAT_VARIABLE)) {
    GlobalFonts.registerFromPath(MONTSERRAT_VARIABLE, "Montserrat");
}

function formatDuration(sec: number) {
    const total = Number.isFinite(sec) && sec > 0 ? sec : 0;
    const m = Math.floor(total / 60);
    const s = Math.floor(total % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
}

function truncate(text: string, maxLen: number) {
    if (text.length <= maxLen) return text;
    return `${text.slice(0, maxLen - 1)}…`;
}

function fitText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number, maxLen: number) {
    let value = truncate(text, maxLen);
    while (value.length > 1 && ctx.measureText(value).width > maxWidth) {
        value = `${value.slice(0, Math.max(1, value.length - 2))}…`;
    }
    return value;
}

function fitTitleFontSize(
    ctx: CanvasRenderingContext2D,
    text: string,
    maxWidth: number,
    maxLen: number,
    startSize: number,
    minSize: number
) {
    const value = truncate(text, maxLen);
    let size = startSize;
    while (size > minSize) {
        ctx.font = `800 ${size}px 'Montserrat', 'Segoe UI', Arial, sans-serif`;
        if (ctx.measureText(value).width <= maxWidth) break;
        size -= 2;
    }
    return { text: value, size };
}

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

export function renderNowPlayingCard(track: QueueTrack, elapsedSeconds: number, artwork: Image | null) {
    const width = 1200;
    const height = 360;
    const coverSize = 328;
    const renderScale = 2;

    const canvas = createCanvas(width * renderScale, height * renderScale);
    const ctx = canvas.getContext("2d");
    ctx.scale(renderScale, renderScale);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";

    if (artwork) {
        const scale = Math.max(width / artwork.width, height / artwork.height);
        const drawW = artwork.width * scale;
        const drawH = artwork.height * scale;
        const drawX = (width - drawW) / 2;
        const drawY = (height - drawH) / 2;

        ctx.save();
        ctx.filter = "blur(14px) saturate(1.1)";
        ctx.drawImage(artwork, drawX, drawY, drawW, drawH);
        ctx.restore();

        const bgGrad = ctx.createLinearGradient(0, 0, width, height);
        bgGrad.addColorStop(0, "rgba(10, 12, 18, 0.40)");
        bgGrad.addColorStop(1, "rgba(16, 18, 26, 0.52)");
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, width, height);
    } else {
        ctx.fillStyle = "#23262d";
        ctx.fillRect(0, 0, width, height);
    }

    const overlay = ctx.createLinearGradient(0, 0, 0, height);
    overlay.addColorStop(0, "rgba(10, 14, 20, 0.34)");
    overlay.addColorStop(1, "rgba(10, 14, 20, 0.24)");
    ctx.fillStyle = overlay;
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    roundedRect(ctx as unknown as CanvasRenderingContext2D, 16, 16, coverSize, coverSize, 20);
    ctx.clip();
    if (artwork) {
        ctx.drawImage(artwork, 16, 16, coverSize, coverSize);
    } else {
        ctx.fillStyle = "#1f2126";
        ctx.fillRect(16, 16, coverSize, coverSize);
    }
    ctx.restore();

    ctx.fillStyle = "rgba(0, 0, 0, 0.36)";
    roundedRect(ctx as unknown as CanvasRenderingContext2D, 16, 16, coverSize, coverSize, 20);
    ctx.fill();

    const textX = 372;
    const textMaxWidth = width - textX - 56;

    ctx.fillStyle = "#f5f7fb";
    const titleFit = fitTitleFontSize(
        ctx as unknown as CanvasRenderingContext2D,
        track.title,
        textMaxWidth,
        54,
        84,
        52
    );
    ctx.font = `800 ${titleFit.size}px 'Montserrat', 'Segoe UI', Arial, sans-serif`;
    ctx.shadowColor = "rgba(0,0,0,0.35)";
    ctx.shadowBlur = 2;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 1;
    ctx.fillText(titleFit.text, textX, 132);

    ctx.fillStyle = "#cfd5df";
    ctx.font = "600 34px 'Montserrat', 'Segoe UI', Arial, sans-serif";
    ctx.shadowColor = "rgba(0,0,0,0.25)";
    ctx.shadowBlur = 1;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 1;
    const primaryArtist = track.artist.split(",")[0]?.trim() || track.artist;
    const artist = fitText(ctx as unknown as CanvasRenderingContext2D, primaryArtist, textMaxWidth, 36);
    const artistY = 132 + Math.max(58, Math.round(titleFit.size * 0.95));
    ctx.fillText(artist, textX, artistY);
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    const barX = textX;
    const barY = 266;
    const barW = width - barX - 56;
    const barH = 9;
    const ratio = track.duration > 0 ? Math.min(1, Math.max(0, elapsedSeconds / track.duration)) : 0;
    const playedW = barW * ratio;

    roundedRect(ctx as unknown as CanvasRenderingContext2D, barX, barY, barW, barH, 6);
    ctx.fillStyle = "rgba(255, 255, 255, 0.28)";
    ctx.fill();

    roundedRect(ctx as unknown as CanvasRenderingContext2D, barX, barY, Math.max(playedW, 8), barH, 6);
    ctx.fillStyle = "#ffffff";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(barX + playedW, barY + barH / 2, 8, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();

    ctx.fillStyle = "#f2f4f8";
    ctx.font = "700 24px 'Montserrat', 'Segoe UI', Arial, sans-serif";
    ctx.fillText(formatDuration(elapsedSeconds), barX, 322);

    const durationText = formatDuration(track.duration);
    const durationWidth = ctx.measureText(durationText).width;
    ctx.fillText(durationText, barX + barW - durationWidth, 322);

    return canvas.toBuffer("image/png");
}
