// Spec2Code Register Map Test IP - AXI4-Lite slave.
//
// Okuma/yazma yolunu BUTUN case'lerle dogrulamak icin uretilmis kucuk bir
// custom IP. Register haritasi (base + offset), Spec2Code Register Map ekranina
// otomatik gelir; ayni haritayla "Canli Izleme"den okuyup yazarak yolun dogru
// oldugunu kanitlarsin:
//
//   0x00 ID             RO  sabit 0x53504543 ("SPEC") - dogru IP/adres kaniti
//   0x04 VERSION        RO  sabit 0x00010000 (MAJOR=1, MINOR=0)
//   0x08 SCRATCH        RW  ne yazarsan aynen okunur
//   0x0C SCRATCH_MIRROR RO  = ~SCRATCH  (SCRATCH'e yazinca degisir -> yaz/oku)
//   0x10 CONTROL        RW  EN[0], MODE[2:1], SPEED[7:4]
//   0x14 STATUS         RO  sabit READY[0]=1, ERROR[1]=0, CODE[15:8]=0xA5
//   0x18 TRIGGER        WO  yazinca COUNTER +1; okuma 0 doner
//   0x1C COUNTER        RO  TRIGGER'a her yazimda +1 (WO->RO etki kaniti)
//
// Standart Xilinx AXI4-Lite slave iskeleti uzerine kurulu; yalniz register
// oku/yaz davranisi ozellestirilmistir.

`timescale 1 ns / 1 ps

module spec2code_regmap_test #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 12
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
    input  wire                             s_axi_rready
);

    // AXI4-Lite handshake kayitlari
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

    localparam integer ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1;  // 2: word secimi
    localparam integer IDX_HI   = ADDR_LSB + 2;                 // 3 bit -> 8 register

    // Ozellestirilen durum
    reg [C_S_AXI_DATA_WIDTH-1 : 0] reg_scratch;   // 0x08
    reg [C_S_AXI_DATA_WIDTH-1 : 0] reg_control;   // 0x10
    reg [C_S_AXI_DATA_WIDTH-1 : 0] reg_counter;   // 0x1C

    localparam [31:0] ID_MAGIC   = 32'h53504543;  // "SPEC"
    localparam [31:0] VERSION_V  = 32'h00010000;  // MAJOR=1, MINOR=0
    localparam [31:0] STATUS_V   = 32'h0000A501;  // CODE=0xA5, ERROR=0, READY=1

    wire                              slv_reg_wren;
    wire                              slv_reg_rden;
    wire [2 : 0]                      waddr_idx = axi_awaddr[IDX_HI : ADDR_LSB];
    wire [2 : 0]                      raddr_idx = axi_araddr[IDX_HI : ADDR_LSB];

    assign s_axi_awready = axi_awready;
    assign s_axi_wready  = axi_wready;
    assign s_axi_bresp   = axi_bresp;
    assign s_axi_bvalid  = axi_bvalid;
    assign s_axi_arready  = axi_arready;
    assign s_axi_rdata   = axi_rdata;
    assign s_axi_rresp   = axi_rresp;
    assign s_axi_rvalid  = axi_rvalid;

    // Yazma adres kanali
    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_awready <= 1'b0;
            axi_awaddr  <= 0;
        end
        else
        begin
            if (~axi_awready && s_axi_awvalid && s_axi_wvalid)
            begin
                axi_awready <= 1'b1;
                axi_awaddr  <= s_axi_awaddr;
            end
            else
            begin
                axi_awready <= 1'b0;
            end
        end
    end

    // Yazma veri kanali
    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
            axi_wready <= 1'b0;
        else if (~axi_wready && s_axi_wvalid && s_axi_awvalid)
            axi_wready <= 1'b1;
        else
            axi_wready <= 1'b0;
    end

    assign slv_reg_wren = axi_wready && s_axi_wvalid && axi_awready && s_axi_awvalid;

    integer byte_index;
    // Yazma davranisi: SCRATCH (0x08), CONTROL (0x10) yazilir; TRIGGER (0x18)
    // yazilinca COUNTER +1. RO register'lara yazma yok sayilir.
    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            reg_scratch <= 0;
            reg_control <= 0;
            reg_counter <= 0;
        end
        else if (slv_reg_wren)
        begin
            case (waddr_idx)
                3'h2: // 0x08 SCRATCH
                    for (byte_index = 0; byte_index < (C_S_AXI_DATA_WIDTH/8); byte_index = byte_index + 1)
                        if (s_axi_wstrb[byte_index] == 1'b1)
                            reg_scratch[byte_index*8 +: 8] <= s_axi_wdata[byte_index*8 +: 8];
                3'h4: // 0x10 CONTROL
                    for (byte_index = 0; byte_index < (C_S_AXI_DATA_WIDTH/8); byte_index = byte_index + 1)
                        if (s_axi_wstrb[byte_index] == 1'b1)
                            reg_control[byte_index*8 +: 8] <= s_axi_wdata[byte_index*8 +: 8];
                3'h6: // 0x18 TRIGGER -> COUNTER +1
                    reg_counter <= reg_counter + 1'b1;
                default: ;
            endcase
        end
    end

    // Yazma cevabi
    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_bvalid <= 1'b0;
            axi_bresp  <= 2'b0;
        end
        else
        begin
            if (axi_awready && s_axi_awvalid && ~axi_bvalid && axi_wready && s_axi_wvalid)
            begin
                axi_bvalid <= 1'b1;
                axi_bresp  <= 2'b0;  // OKAY
            end
            else if (s_axi_bready && axi_bvalid)
                axi_bvalid <= 1'b0;
        end
    end

    // Okuma adres kanali
    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_arready <= 1'b0;
            axi_araddr  <= 0;
        end
        else
        begin
            if (~axi_arready && s_axi_arvalid)
            begin
                axi_arready <= 1'b1;
                axi_araddr  <= s_axi_araddr;
            end
            else
                axi_arready <= 1'b0;
        end
    end

    // Okuma gecerli
    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
        begin
            axi_rvalid <= 1'b0;
            axi_rresp  <= 2'b0;
        end
        else
        begin
            if (axi_arready && s_axi_arvalid && ~axi_rvalid)
            begin
                axi_rvalid <= 1'b1;
                axi_rresp  <= 2'b0;  // OKAY
            end
            else if (axi_rvalid && s_axi_rready)
                axi_rvalid <= 1'b0;
        end
    end

    assign slv_reg_rden = axi_arready & s_axi_arvalid & ~axi_rvalid;

    // Okuma davranisi (register haritasi)
    reg [C_S_AXI_DATA_WIDTH-1 : 0] read_value;
    always @(*)
    begin
        case (raddr_idx)
            3'h0: read_value = ID_MAGIC;          // 0x00 ID
            3'h1: read_value = VERSION_V;         // 0x04 VERSION
            3'h2: read_value = reg_scratch;       // 0x08 SCRATCH
            3'h3: read_value = ~reg_scratch;      // 0x0C SCRATCH_MIRROR
            3'h4: read_value = reg_control;       // 0x10 CONTROL
            3'h5: read_value = STATUS_V;          // 0x14 STATUS
            3'h6: read_value = 32'h00000000;      // 0x18 TRIGGER (WO)
            3'h7: read_value = reg_counter;       // 0x1C COUNTER
            default: read_value = 32'h00000000;
        endcase
    end

    always @(posedge s_axi_aclk)
    begin
        if (s_axi_aresetn == 1'b0)
            axi_rdata <= 0;
        else if (slv_reg_rden)
            axi_rdata <= read_value;
    end

endmodule
