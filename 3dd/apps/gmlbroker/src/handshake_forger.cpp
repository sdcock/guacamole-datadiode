#include "../include/handshake_forger.h"
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

namespace {

// Build one Guacamole instruction from its elements: "len.elem,len.elem,...;"
std::string instr(const std::vector<std::string> &elems) {
    std::string s;
    for (size_t i = 0; i < elems.size(); ++i) {
        s += std::to_string(elems[i].size());
        s += '.';
        s += elems[i];
        s += (i + 1 < elems.size()) ? ',' : ';';
    }
    return s;
}

// "Waiting for approval..." rendered white on a transparent canvas, baked once
// with PIL (Cantarell 40px). Painted OVER the grey waiting layer, so only the
// glyphs show. Because gmlbroker draws the waiting screen straight to the
// browser on the return path, this never crosses the guard — the opcode
// allowlist and the 50-byte clipboard blob cap do not apply.
constexpr int kWaitImgW = 454;
constexpr int kWaitImgH = 79;
const char *kWaitImgPngB64 =
    "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";

// A v4-style UUID prefixed with '$', matching guacd's connection-id format
// (e.g. "$79fce574-83ce-4418-a9e5-949b5c4e482b", 37 chars).
std::string make_fake_id() {
    static thread_local std::mt19937_64 rng{std::random_device{}()};
    std::uniform_int_distribution<int> hex(0, 15);
    const char *digits = "0123456789abcdef";
    std::string id = "$";
    for (int i = 0; i < 32; ++i) {
        if (i == 8 || i == 12 || i == 16 || i == 20)
            id += '-';
        id += digits[hex(rng)];
    }
    return id;
}

// Canned `args` reply for ssh, captured verbatim from guacd 1.6.0 (43 elements:
// the VERSION token plus 42 parameter names). The count and ordering must match
// guacd exactly: the browser builds `connect` with one value per arg in this
// list, and the real guacd validates that count when the handshake is replayed.
// guacd 1.6.0 adds `timeout`, `public-key`, `typescript-write-existing`, and
// `recording-write-existing` over the 1.5.0 list.
const char *SSH_ARGS_1_6_0 =
    "4.args,13.VERSION_1_5_0,8.hostname,8.host-key,4.port,7.timeout,8.username,"
    "8.password,9.font-name,9.font-size,11.enable-sftp,19.sftp-root-directory,"
    "21.sftp-disable-download,19.sftp-disable-upload,11.private-key,"
    "10.passphrase,10.public-key,12.color-scheme,7.command,15.typescript-path,"
    "15.typescript-name,22.create-typescript-path,25.typescript-write-existing,"
    "14.recording-path,14.recording-name,24.recording-exclude-output,"
    "23.recording-exclude-mouse,22.recording-include-keys,"
    "21.create-recording-path,24.recording-write-existing,9.read-only,"
    "21.server-alive-interval,9.backspace,13.terminal-type,10.scrollback,"
    "6.locale,8.timezone,12.disable-copy,13.disable-paste,15.wol-send-packet,"
    "12.wol-mac-addr,18.wol-broadcast-addr,12.wol-udp-port,13.wol-wait-time;";

// Canned `args` reply for rdp, captured verbatim from guacd 1.6.0 (89 elements:
// the VERSION token plus 88 parameter names). Same rule as ssh: the count and
// ordering must match guacd exactly, since the browser's `connect` is positional
// against this list and the real guacd validates the count on replay.
const char *RDP_ARGS_1_6_0 =
    "4.args,13.VERSION_1_5_0,8.hostname,4.port,7.timeout,6.domain,"
    "8.username,8.password,5.width,6.height,3.dpi,15.initial-program,"
    "11.color-depth,13.disable-audio,15.enable-printing,12.printer-name,"
    "12.enable-drive,10.drive-name,10.drive-path,17.create-drive-path,"
    "16.disable-download,14.disable-upload,7.console,13.console-audio,"
    "13.server-layout,8.security,11.ignore-cert,9.cert-tofu,"
    "17.cert-fingerprints,12.disable-auth,10.remote-app,"
    "14.remote-app-dir,15.remote-app-args,15.static-channels,"
    "11.client-name,16.enable-wallpaper,14.enable-theming,"
    "21.enable-font-smoothing,23.enable-full-window-drag,"
    "26.enable-desktop-composition,22.enable-menu-animations,"
    "22.disable-bitmap-caching,25.disable-offscreen-caching,"
    "21.disable-glyph-caching,11.disable-gfx,16.preconnection-id,"
    "18.preconnection-blob,8.timezone,11.enable-sftp,13.sftp-hostname,"
    "13.sftp-host-key,9.sftp-port,12.sftp-timeout,13.sftp-username,"
    "13.sftp-password,16.sftp-private-key,15.sftp-passphrase,"
    "15.sftp-public-key,14.sftp-directory,19.sftp-root-directory,"
    "26.sftp-server-alive-interval,21.sftp-disable-download,"
    "19.sftp-disable-upload,14.recording-path,14.recording-name,"
    "24.recording-exclude-output,23.recording-exclude-mouse,"
    "23.recording-exclude-touch,22.recording-include-keys,"
    "21.create-recording-path,24.recording-write-existing,"
    "13.resize-method,18.enable-audio-input,12.enable-touch,9.read-only,"
    "16.gateway-hostname,12.gateway-port,14.gateway-domain,"
    "16.gateway-username,16.gateway-password,17.load-balance-info,"
    "12.disable-copy,13.disable-paste,15.wol-send-packet,12.wol-mac-addr,"
    "18.wol-broadcast-addr,12.wol-udp-port,13.wol-wait-time,"
    "14.force-lossless,19.normalize-clipboard;";

} // namespace

std::string HandshakeForger::Feed(const char *data, size_t len) {
    out.clear();
    // Keep a verbatim copy of the handshake so it can be replayed to the real
    // guacd once approved. (Feed is only called before ESTABLISHED.)
    handshake_raw.append(data, len);
    Parse(data, len);
    if (GetState() == ParserState::STREAM_CORRUPTED)
        hs_state = HandshakeState::INVALID_HANDSHAKE;
    return out;
}

bool HandshakeForger::OnInstructionBegin(const GuacElement &instr) {
    current_opcode.assign(instr.ptr, instr.len);
    // The forger is not a security gate; accept every handshake opcode.
    return true;
}

bool HandshakeForger::OnArgument(const GuacElement &arg) {
    if (current_opcode == "select")
        protocol.assign(arg.ptr, arg.len);
    else if (current_opcode == "connect")
        connect_values.emplace_back(arg.ptr, arg.len);
    else if (current_opcode == "size")
        size_args.emplace_back(arg.ptr, arg.len);
    return true;
}

bool HandshakeForger::OnInstructionEnd() {
    // After select was sent, send fake connection parameters
    if (current_opcode == "select") {
        out += CannedArgs();
        hs_state = HandshakeState::EXCHANGING_PARAMETERS;
    } else if (current_opcode == "connect") {
        // When connect is received send a ready instruction with a fake ID
        fake_id = make_fake_id();
        out += instr({"ready", fake_id});
        out += WaitingScreen();
        hs_state = HandshakeState::ESTABLISHED;
    }
    return true;
}

std::string HandshakeForger::CannedArgs() const {
    // Per-protocol canned args, pinned to guacd 1.6.0. Extend as more protocols
    // are wired up; the forged list must match guacd's real args exactly.
    if (protocol == "rdp")
        return RDP_ARGS_1_6_0;
    if (protocol == "ssh")
        return SSH_ARGS_1_6_0;
    return SSH_ARGS_1_6_0; // PoC fallback
}

std::string HandshakeForger::WaitingScreen() const {
    // Paint the default layer solid dark grey, then overlay the baked
    // "Waiting for approval..." text image centred on it.
    std::string w = size_args.size() > 0 ? size_args[0] : "1024";
    std::string h = size_args.size() > 1 ? size_args[1] : "768";

    std::string s;
    s += instr({"size", "0", w, h});                  // size default layer (0)
    s += instr({"rect", "0", "0", "0", w, h});        // full-layer rectangle
    s += instr({"cfill", "14", "0", "40", "40", "40", "255"}); // OVER, dark grey

    // Overlay the text, centred. The PNG is transparent-backed white glyphs, so
    // OVER (mode 14) paints only the lettering onto the grey. The image stream
    // is opened (img), fed base64 in bounded blobs, then closed (end).
    int wi = std::atoi(w.c_str());
    int hi = std::atoi(h.c_str());
    std::string x = std::to_string(wi > kWaitImgW ? (wi - kWaitImgW) / 2 : 0);
    std::string y = std::to_string(hi > kWaitImgH ? (hi - kWaitImgH) / 2 : 0);
    const std::string stream = "1";                    // ephemeral image stream
    s += instr({"img", stream, "14", "0", "image/png", x, y});
    std::string b64 = kWaitImgPngB64;
    for (size_t off = 0; off < b64.size(); off += 4096)
        s += instr({"blob", stream, b64.substr(off, 4096)});
    s += instr({"end", stream});

    s += instr({"sync", "0"});                         // close the frame
    return s;
}

std::string HandshakeForger::DeniedScreen() {
    // Generous default dimensions: exact size is unimportant for an error
    // overlay. Paint the default layer solid red, then ask the client to leave.
    std::string s;
    s += instr({"size", "0", "1024", "768"});
    s += instr({"rect", "0", "0", "0", "1024", "768"});
    s += instr({"cfill", "14", "0", "180", "30", "30", "255"}); // OVER, red
    s += instr({"sync", "0"});
    s += instr({"disconnect"});
    return s;
}
