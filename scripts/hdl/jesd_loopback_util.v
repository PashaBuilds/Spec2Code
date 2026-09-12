// Spec2Code JESD204C loopback yardimcisi - AXI4-Lite slave (KV260 PL ici TX->RX loopback tasarimi).
//
// Iki is yapar:
//   1) RX yakalama: JESD204C RX cekirdeginin m_axis_rx cikisini (rx_tdata 256 bit = 16 x int16 ornek,
//      rx_tvalid) ARM verilince DEPTH beat boyunca BRAM'e yazar; PS, AXI-Lite veri penceresinden
//      (0x8000-0xFFFF, 32-bit sozcukler) okur (ajan `mem_block` op'u -> Spec2Code Yakalama ekrani:
//      ham cizim + FFT).
//   2) TX desen: JESD204C TX cekirdegine (s_axis_tx, tx_tdata) 16 bit sinus ornekleri uretir
//      (NCO: 16-bit faz, 256 girisli tam dalga ROM, faz artisi TX_PHASE_INC register'i).
//      Beat basina 16 ornek: tx_tdata[16*i +: 16] = ornek i (i=0 en eski). Ornekleme hizi
//      = 16 x core_clk (100 MHz pl_clk0 -> 1.6 GS/s esdegeri; ton frekansi = INC/65536 x fs).
//
// Register haritasi (base + offset; s_axi_aclk == core_clk varsayilir, ayni pl_clk0):
//   0x00 ID            RO  0x43415054 ("CAPT")
//   0x04 VERSION       RO  0x00010000
//   0x08 CTRL          RW  ARM[0] (1 yaz: yakalama baslar, bitince kendiliginden 0), CLEAR[1] (DONE/COUNT sifirla)
//   0x0C STATUS        RO  DONE[0], BUSY[1], RX_VALID_SEEN[2] (yapiskan: rx_tvalid hic geldi mi)
//   0x10 COUNT         RO  yakalanan beat sayisi (0..DEPTH)
//   0x14 DEPTH         RO  DEPTH (beat)
//   0x18 BEAT_BITS     RO  256
//   0x1C TX_PHASE_INC  RW  NCO faz artisi (varsayilan 0x0400 = fs/64 tonu)
//   0x20 DATA_OFFSET   RO  0x8000 (veri penceresinin baslangici)
//   0x24 TX_BEATS      RO  gonderilen TX beat sayaci (canlilik)
//   0x28 RX_BEATS      RO  gorulen rx_tvalid beat sayaci (canlilik)
//   0x8000.. DATA      RO  beat k, 32-bit dilim j: 0x8000 + k*32 + j*4  (dilim j = ornek 2j (dusuk 16 bit), 2j+1)
//
// AXI4-Lite iskeleti: backend/data/spec2code_regmap_test.v ile ayni handshake; okuma yolu BRAM icin
// bir cevrim daha bekler (adres kabul -> BRAM okuma -> RVALID).

`timescale 1 ns / 1 ps

module jesd_loopback_util #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 16,
    parameter integer DEPTH = 1024
)
(
    input  wire                             s_axi_aclk,
    input  wire                             s_axi_aresetn,
    input  wire [C_S_AXI_ADDR_WIDTH-1 : 0]  s_axi_awaddr,
    input  wire [2 : 0]                      s_axi_awprot,
    input  wire                             s_axi_awvalid,
    output wire                             s_axi_awready,
    input  wire [C_S_AXI_DATA_WIDTH-1 : 0]  s_axi_wdata,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0] s_axi_wstrb,
    input  wire                             s_axi_wvalid,
    output wire                             s_axi_wready,
    output wire [1 : 0]                      s_axi_bresp,
    output wire                             s_axi_bvalid,
    input  wire                             s_axi_bready,
    input  wire [C_S_AXI_ADDR_WIDTH-1 : 0]  s_axi_araddr,
    input  wire [2 : 0]                      s_axi_arprot,
    input  wire                             s_axi_arvalid,
    output wire                             s_axi_arready,
    output wire [C_S_AXI_DATA_WIDTH-1 : 0]  s_axi_rdata,
    output wire [1 : 0]                      s_axi_rresp,
    output wire                             s_axi_rvalid,
    input  wire                             s_axi_rready,
    // JESD204C cekirdek tarafi (core_clk = s_axi_aclk = pl_clk0)
    input  wire                             core_clk,
    input  wire                             core_rst,        // aktif yuksek (proc_sys_reset peripheral_reset)
    input  wire [255 : 0]                   rx_tdata,
    input  wire                             rx_tvalid,
    output reg  [255 : 0]                   tx_tdata,
    input  wire                             tx_tready
);

    localparam [31:0] ID_MAGIC  = 32'h43415054;  // "CAPT"
    localparam [31:0] VERSION_V = 32'h00010000;
    localparam integer AW = 10;                  // log2(DEPTH=1024)

    // ---------------- AXI4-Lite handshake ----------------
    reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_awaddr;
    reg                           axi_awready;
    reg                           axi_wready;
    reg [1 : 0]                   axi_bresp;
    reg                           axi_bvalid;
    reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_araddr;
    reg                           axi_arready;
    reg [C_S_AXI_DATA_WIDTH-1 : 0] axi_rdata;
    reg [1 : 0]                   axi_rresp;
    reg                           axi_rvalid;
    reg                           rd_pending;

    assign s_axi_awready = axi_awready;
    assign s_axi_wready  = axi_wready;
    assign s_axi_bresp   = axi_bresp;
    assign s_axi_bvalid  = axi_bvalid;
    assign s_axi_arready = axi_arready;
    assign s_axi_rdata   = axi_rdata;
    assign s_axi_rresp   = axi_rresp;
    assign s_axi_rvalid  = axi_rvalid;

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_awready <= 1'b0;
            axi_awaddr  <= 0;
        end
        else if (~axi_awready && s_axi_awvalid && s_axi_wvalid)
        begin
            axi_awready <= 1'b1;
            axi_awaddr  <= s_axi_awaddr;
        end
        else
            axi_awready <= 1'b0;
    end

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
            axi_wready <= 1'b0;
        else if (~axi_wready && s_axi_wvalid && s_axi_awvalid)
            axi_wready <= 1'b1;
        else
            axi_wready <= 1'b0;
    end

    wire slv_reg_wren = axi_wready && s_axi_wvalid && axi_awready && s_axi_awvalid;
    wire [3:0] waddr_idx = axi_awaddr[5:2];
    wire       waddr_is_reg = (axi_awaddr[C_S_AXI_ADDR_WIDTH-1:6] == 0);

    // ---------------- Kontrol / durum ----------------
    reg          armed;
    reg          done;
    reg          rx_seen;
    reg [AW:0]   wr_ptr;          // 0..DEPTH
    reg [31:0]   tx_phase_inc;
    reg [31:0]   tx_beats;
    reg [31:0]   rx_beats;
    reg          arm_req;
    reg          clear_req;

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            tx_phase_inc <= 32'h00000400;
            arm_req      <= 1'b0;
            clear_req    <= 1'b0;
        end
        else
        begin
            arm_req   <= 1'b0;
            clear_req <= 1'b0;
            if (slv_reg_wren && waddr_is_reg)
            begin
                case (waddr_idx)
                    4'h2: begin              // 0x08 CTRL
                        if (s_axi_wstrb[0]) begin
                            arm_req   <= s_axi_wdata[0];
                            clear_req <= s_axi_wdata[1];
                        end
                    end
                    4'h7: begin              // 0x1C TX_PHASE_INC
                        if (s_axi_wstrb[0]) tx_phase_inc[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) tx_phase_inc[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) tx_phase_inc[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) tx_phase_inc[31:24] <= s_axi_wdata[31:24];
                    end
                    default: ;
                endcase
            end
        end
    end

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_bvalid <= 1'b0;
            axi_bresp  <= 2'b0;
        end
        else if (axi_awready && s_axi_awvalid && ~axi_bvalid && axi_wready && s_axi_wvalid)
        begin
            axi_bvalid <= 1'b1;
            axi_bresp  <= 2'b0;
        end
        else if (s_axi_bready && axi_bvalid)
            axi_bvalid <= 1'b0;
    end

    // ---------------- Yakalama BRAM (256 bit x DEPTH) ----------------
    reg [255:0] mem [0:DEPTH-1];
    reg [255:0] mem_q;

    always @(posedge core_clk)
    begin
        if (core_rst)
        begin
            armed    <= 1'b0;
            done     <= 1'b0;
            rx_seen  <= 1'b0;
            wr_ptr   <= 0;
            rx_beats <= 32'd0;
        end
        else
        begin
            if (rx_tvalid)
            begin
                rx_seen  <= 1'b1;
                rx_beats <= rx_beats + 32'd1;
            end
            if (clear_req)
            begin
                done   <= 1'b0;
                wr_ptr <= 0;
                armed  <= 1'b0;
            end
            else if (arm_req && !armed)
            begin
                armed  <= 1'b1;
                done   <= 1'b0;
                wr_ptr <= 0;
            end
            else if (armed && rx_tvalid)
            begin
                mem[wr_ptr[AW-1:0]] <= rx_tdata;
                if (wr_ptr == DEPTH - 1)
                begin
                    armed <= 1'b0;
                    done  <= 1'b1;
                end
                wr_ptr <= wr_ptr + 1'b1;
            end
        end
    end

    // ---------------- TX sinus NCO ----------------
    function [15:0] sine_rom;
        input [7:0] idx;
        begin
            case (idx)
            8'd0: sine_rom = 16'h0000;
            8'd1: sine_rom = 16'h02E0;
            8'd2: sine_rom = 16'h05C0;
            8'd3: sine_rom = 16'h089F;
            8'd4: sine_rom = 16'h0B7D;
            8'd5: sine_rom = 16'h0E58;
            8'd6: sine_rom = 16'h1132;
            8'd7: sine_rom = 16'h1409;
            8'd8: sine_rom = 16'h16DD;
            8'd9: sine_rom = 16'h19AD;
            8'd10: sine_rom = 16'h1C79;
            8'd11: sine_rom = 16'h1F41;
            8'd12: sine_rom = 16'h2205;
            8'd13: sine_rom = 16'h24C2;
            8'd14: sine_rom = 16'h277B;
            8'd15: sine_rom = 16'h2A2D;
            8'd16: sine_rom = 16'h2CD9;
            8'd17: sine_rom = 16'h2F7D;
            8'd18: sine_rom = 16'h321B;
            8'd19: sine_rom = 16'h34B0;
            8'd20: sine_rom = 16'h373E;
            8'd21: sine_rom = 16'h39C3;
            8'd22: sine_rom = 16'h3C3F;
            8'd23: sine_rom = 16'h3EB2;
            8'd24: sine_rom = 16'h411B;
            8'd25: sine_rom = 16'h437A;
            8'd26: sine_rom = 16'h45CF;
            8'd27: sine_rom = 16'h4819;
            8'd28: sine_rom = 16'h4A58;
            8'd29: sine_rom = 16'h4C8B;
            8'd30: sine_rom = 16'h4EB3;
            8'd31: sine_rom = 16'h50CE;
            8'd32: sine_rom = 16'h52DD;
            8'd33: sine_rom = 16'h54DF;
            8'd34: sine_rom = 16'h56D5;
            8'd35: sine_rom = 16'h58BC;
            8'd36: sine_rom = 16'h5A96;
            8'd37: sine_rom = 16'h5C62;
            8'd38: sine_rom = 16'h5E20;
            8'd39: sine_rom = 16'h5FD0;
            8'd40: sine_rom = 16'h6170;
            8'd41: sine_rom = 16'h6302;
            8'd42: sine_rom = 16'h6484;
            8'd43: sine_rom = 16'h65F7;
            8'd44: sine_rom = 16'h675A;
            8'd45: sine_rom = 16'h68AD;
            8'd46: sine_rom = 16'h69F0;
            8'd47: sine_rom = 16'h6B22;
            8'd48: sine_rom = 16'h6C44;
            8'd49: sine_rom = 16'h6D56;
            8'd50: sine_rom = 16'h6E56;
            8'd51: sine_rom = 16'h6F46;
            8'd52: sine_rom = 16'h7024;
            8'd53: sine_rom = 16'h70F1;
            8'd54: sine_rom = 16'h71AD;
            8'd55: sine_rom = 16'h7257;
            8'd56: sine_rom = 16'h72F0;
            8'd57: sine_rom = 16'h7376;
            8'd58: sine_rom = 16'h73EB;
            8'd59: sine_rom = 16'h744E;
            8'd60: sine_rom = 16'h74A0;
            8'd61: sine_rom = 16'h74DF;
            8'd62: sine_rom = 16'h750C;
            8'd63: sine_rom = 16'h7527;
            8'd64: sine_rom = 16'h7530;
            8'd65: sine_rom = 16'h7527;
            8'd66: sine_rom = 16'h750C;
            8'd67: sine_rom = 16'h74DF;
            8'd68: sine_rom = 16'h74A0;
            8'd69: sine_rom = 16'h744E;
            8'd70: sine_rom = 16'h73EB;
            8'd71: sine_rom = 16'h7376;
            8'd72: sine_rom = 16'h72F0;
            8'd73: sine_rom = 16'h7257;
            8'd74: sine_rom = 16'h71AD;
            8'd75: sine_rom = 16'h70F1;
            8'd76: sine_rom = 16'h7024;
            8'd77: sine_rom = 16'h6F46;
            8'd78: sine_rom = 16'h6E56;
            8'd79: sine_rom = 16'h6D56;
            8'd80: sine_rom = 16'h6C44;
            8'd81: sine_rom = 16'h6B22;
            8'd82: sine_rom = 16'h69F0;
            8'd83: sine_rom = 16'h68AD;
            8'd84: sine_rom = 16'h675A;
            8'd85: sine_rom = 16'h65F7;
            8'd86: sine_rom = 16'h6484;
            8'd87: sine_rom = 16'h6302;
            8'd88: sine_rom = 16'h6170;
            8'd89: sine_rom = 16'h5FD0;
            8'd90: sine_rom = 16'h5E20;
            8'd91: sine_rom = 16'h5C62;
            8'd92: sine_rom = 16'h5A96;
            8'd93: sine_rom = 16'h58BC;
            8'd94: sine_rom = 16'h56D5;
            8'd95: sine_rom = 16'h54DF;
            8'd96: sine_rom = 16'h52DD;
            8'd97: sine_rom = 16'h50CE;
            8'd98: sine_rom = 16'h4EB3;
            8'd99: sine_rom = 16'h4C8B;
            8'd100: sine_rom = 16'h4A58;
            8'd101: sine_rom = 16'h4819;
            8'd102: sine_rom = 16'h45CF;
            8'd103: sine_rom = 16'h437A;
            8'd104: sine_rom = 16'h411B;
            8'd105: sine_rom = 16'h3EB2;
            8'd106: sine_rom = 16'h3C3F;
            8'd107: sine_rom = 16'h39C3;
            8'd108: sine_rom = 16'h373E;
            8'd109: sine_rom = 16'h34B0;
            8'd110: sine_rom = 16'h321B;
            8'd111: sine_rom = 16'h2F7D;
            8'd112: sine_rom = 16'h2CD9;
            8'd113: sine_rom = 16'h2A2D;
            8'd114: sine_rom = 16'h277B;
            8'd115: sine_rom = 16'h24C2;
            8'd116: sine_rom = 16'h2205;
            8'd117: sine_rom = 16'h1F41;
            8'd118: sine_rom = 16'h1C79;
            8'd119: sine_rom = 16'h19AD;
            8'd120: sine_rom = 16'h16DD;
            8'd121: sine_rom = 16'h1409;
            8'd122: sine_rom = 16'h1132;
            8'd123: sine_rom = 16'h0E58;
            8'd124: sine_rom = 16'h0B7D;
            8'd125: sine_rom = 16'h089F;
            8'd126: sine_rom = 16'h05C0;
            8'd127: sine_rom = 16'h02E0;
            8'd128: sine_rom = 16'h0000;
            8'd129: sine_rom = 16'hFD20;
            8'd130: sine_rom = 16'hFA40;
            8'd131: sine_rom = 16'hF761;
            8'd132: sine_rom = 16'hF483;
            8'd133: sine_rom = 16'hF1A8;
            8'd134: sine_rom = 16'hEECE;
            8'd135: sine_rom = 16'hEBF7;
            8'd136: sine_rom = 16'hE923;
            8'd137: sine_rom = 16'hE653;
            8'd138: sine_rom = 16'hE387;
            8'd139: sine_rom = 16'hE0BF;
            8'd140: sine_rom = 16'hDDFB;
            8'd141: sine_rom = 16'hDB3E;
            8'd142: sine_rom = 16'hD885;
            8'd143: sine_rom = 16'hD5D3;
            8'd144: sine_rom = 16'hD327;
            8'd145: sine_rom = 16'hD083;
            8'd146: sine_rom = 16'hCDE5;
            8'd147: sine_rom = 16'hCB50;
            8'd148: sine_rom = 16'hC8C2;
            8'd149: sine_rom = 16'hC63D;
            8'd150: sine_rom = 16'hC3C1;
            8'd151: sine_rom = 16'hC14E;
            8'd152: sine_rom = 16'hBEE5;
            8'd153: sine_rom = 16'hBC86;
            8'd154: sine_rom = 16'hBA31;
            8'd155: sine_rom = 16'hB7E7;
            8'd156: sine_rom = 16'hB5A8;
            8'd157: sine_rom = 16'hB375;
            8'd158: sine_rom = 16'hB14D;
            8'd159: sine_rom = 16'hAF32;
            8'd160: sine_rom = 16'hAD23;
            8'd161: sine_rom = 16'hAB21;
            8'd162: sine_rom = 16'hA92B;
            8'd163: sine_rom = 16'hA744;
            8'd164: sine_rom = 16'hA56A;
            8'd165: sine_rom = 16'hA39E;
            8'd166: sine_rom = 16'hA1E0;
            8'd167: sine_rom = 16'hA030;
            8'd168: sine_rom = 16'h9E90;
            8'd169: sine_rom = 16'h9CFE;
            8'd170: sine_rom = 16'h9B7C;
            8'd171: sine_rom = 16'h9A09;
            8'd172: sine_rom = 16'h98A6;
            8'd173: sine_rom = 16'h9753;
            8'd174: sine_rom = 16'h9610;
            8'd175: sine_rom = 16'h94DE;
            8'd176: sine_rom = 16'h93BC;
            8'd177: sine_rom = 16'h92AA;
            8'd178: sine_rom = 16'h91AA;
            8'd179: sine_rom = 16'h90BA;
            8'd180: sine_rom = 16'h8FDC;
            8'd181: sine_rom = 16'h8F0F;
            8'd182: sine_rom = 16'h8E53;
            8'd183: sine_rom = 16'h8DA9;
            8'd184: sine_rom = 16'h8D10;
            8'd185: sine_rom = 16'h8C8A;
            8'd186: sine_rom = 16'h8C15;
            8'd187: sine_rom = 16'h8BB2;
            8'd188: sine_rom = 16'h8B60;
            8'd189: sine_rom = 16'h8B21;
            8'd190: sine_rom = 16'h8AF4;
            8'd191: sine_rom = 16'h8AD9;
            8'd192: sine_rom = 16'h8AD0;
            8'd193: sine_rom = 16'h8AD9;
            8'd194: sine_rom = 16'h8AF4;
            8'd195: sine_rom = 16'h8B21;
            8'd196: sine_rom = 16'h8B60;
            8'd197: sine_rom = 16'h8BB2;
            8'd198: sine_rom = 16'h8C15;
            8'd199: sine_rom = 16'h8C8A;
            8'd200: sine_rom = 16'h8D10;
            8'd201: sine_rom = 16'h8DA9;
            8'd202: sine_rom = 16'h8E53;
            8'd203: sine_rom = 16'h8F0F;
            8'd204: sine_rom = 16'h8FDC;
            8'd205: sine_rom = 16'h90BA;
            8'd206: sine_rom = 16'h91AA;
            8'd207: sine_rom = 16'h92AA;
            8'd208: sine_rom = 16'h93BC;
            8'd209: sine_rom = 16'h94DE;
            8'd210: sine_rom = 16'h9610;
            8'd211: sine_rom = 16'h9753;
            8'd212: sine_rom = 16'h98A6;
            8'd213: sine_rom = 16'h9A09;
            8'd214: sine_rom = 16'h9B7C;
            8'd215: sine_rom = 16'h9CFE;
            8'd216: sine_rom = 16'h9E90;
            8'd217: sine_rom = 16'hA030;
            8'd218: sine_rom = 16'hA1E0;
            8'd219: sine_rom = 16'hA39E;
            8'd220: sine_rom = 16'hA56A;
            8'd221: sine_rom = 16'hA744;
            8'd222: sine_rom = 16'hA92B;
            8'd223: sine_rom = 16'hAB21;
            8'd224: sine_rom = 16'hAD23;
            8'd225: sine_rom = 16'hAF32;
            8'd226: sine_rom = 16'hB14D;
            8'd227: sine_rom = 16'hB375;
            8'd228: sine_rom = 16'hB5A8;
            8'd229: sine_rom = 16'hB7E7;
            8'd230: sine_rom = 16'hBA31;
            8'd231: sine_rom = 16'hBC86;
            8'd232: sine_rom = 16'hBEE5;
            8'd233: sine_rom = 16'hC14E;
            8'd234: sine_rom = 16'hC3C1;
            8'd235: sine_rom = 16'hC63D;
            8'd236: sine_rom = 16'hC8C2;
            8'd237: sine_rom = 16'hCB50;
            8'd238: sine_rom = 16'hCDE5;
            8'd239: sine_rom = 16'hD083;
            8'd240: sine_rom = 16'hD327;
            8'd241: sine_rom = 16'hD5D3;
            8'd242: sine_rom = 16'hD885;
            8'd243: sine_rom = 16'hDB3E;
            8'd244: sine_rom = 16'hDDFB;
            8'd245: sine_rom = 16'hE0BF;
            8'd246: sine_rom = 16'hE387;
            8'd247: sine_rom = 16'hE653;
            8'd248: sine_rom = 16'hE923;
            8'd249: sine_rom = 16'hEBF7;
            8'd250: sine_rom = 16'hEECE;
            8'd251: sine_rom = 16'hF1A8;
            8'd252: sine_rom = 16'hF483;
            8'd253: sine_rom = 16'hF761;
            8'd254: sine_rom = 16'hFA40;
            8'd255: sine_rom = 16'hFD20;
            endcase
        end
    endfunction

    reg  [15:0] phase;
    integer     s;
    reg  [15:0] ph_i;
    always @(posedge core_clk)
    begin
        if (core_rst)
        begin
            phase    <= 16'd0;
            tx_tdata <= 256'd0;
            tx_beats <= 32'd0;
        end
        else
        begin
            for (s = 0; s < 16; s = s + 1)
            begin
                ph_i = phase + s * tx_phase_inc[15:0];
                tx_tdata[16*s +: 16] <= sine_rom(ph_i[15:8]);
            end
            phase    <= phase + 16 * tx_phase_inc[15:0];
            tx_beats <= tx_beats + 32'd1;
        end
    end

    // ---------------- Okuma yolu ----------------
    wire [3:0] raddr_idx = axi_araddr[5:2];
    wire       raddr_is_data = axi_araddr[15];
    reg  [2:0] rd_slice;
    reg  [31:0] reg_val;
    reg        rd_is_data;

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_arready <= 1'b0;
            axi_araddr  <= 0;
        end
        else if (~axi_arready && s_axi_arvalid && ~axi_rvalid && ~rd_pending)
        begin
            axi_arready <= 1'b1;
            axi_araddr  <= s_axi_araddr;
        end
        else
            axi_arready <= 1'b0;
    end

    wire slv_reg_rden = axi_arready & s_axi_arvalid & ~axi_rvalid & ~rd_pending;

    reg [31:0] read_value;
    always @(*)
    begin
        case (raddr_idx)
            4'h0: read_value = ID_MAGIC;
            4'h1: read_value = VERSION_V;
            4'h2: read_value = {30'd0, 1'b0, armed};
            4'h3: read_value = {29'd0, rx_seen, armed, done};
            4'h4: read_value = {{(31-AW){1'b0}}, wr_ptr};
            4'h5: read_value = DEPTH;
            4'h6: read_value = 32'd256;
            4'h7: read_value = tx_phase_inc;
            4'h8: read_value = 32'h00008000;
            4'h9: read_value = tx_beats;
            4'hA: read_value = rx_beats;
            default: read_value = 32'h00000000;
        endcase
    end

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            rd_pending <= 1'b0;
            axi_rvalid <= 1'b0;
            axi_rresp  <= 2'b0;
            axi_rdata  <= 0;
            rd_is_data <= 1'b0;
            rd_slice   <= 3'd0;
            reg_val    <= 32'd0;
            mem_q      <= 256'd0;
        end
        else
        begin
            if (slv_reg_rden)
            begin
                rd_pending <= 1'b1;
                rd_is_data <= raddr_is_data;
                rd_slice   <= axi_araddr[4:2];
                reg_val    <= read_value;
                mem_q      <= mem[axi_araddr[5 +: AW]];
            end
            else if (rd_pending)
            begin
                rd_pending <= 1'b0;
                axi_rvalid <= 1'b1;
                axi_rresp  <= 2'b0;
                axi_rdata  <= rd_is_data ? mem_q[rd_slice*32 +: 32] : reg_val;
            end
            else if (axi_rvalid && s_axi_rready)
                axi_rvalid <= 1'b0;
        end
    end

endmodule
