// RMII (PHY, 50 MHz REF_CLK) <-> MII (AXI EthernetLite, 25 MHz) adaptoru - Spec2Code Nexys A7
// referans tasarimi. Vivado 2023.x katalogunda Xilinx `mii_to_rmii` IP'si olmadigi icin (obsolete)
// kendi adaptorumuz. Butun mantik ref_clk (50 MHz) alaninda; MII saatleri ref_clk/2'nin BUFG'li
// bolunmus kopyasidir (XDC: create_generated_clock clk25_reg).
//
// RX: RMII dibitleri nibble'a toplanir. Hizalama SFD ile yapilir: cerceve icindeki ilk "11" dibiti
//     SFD (0xD5 = 01 01 01 11) nibble'inin IKINCI yarisidir; preamble'in olasi "00" onunu atmak icin
//     rx_dv ilk "01" dibitinde kalkar. CRS_DV: nibble'in ikinci dibitinde DV'yi tasir (RMII spec).
// TX: MII nibble clk25'in dusen kenarinda (MAC cikislari kararli) orneklenir, iki dibit olarak
//     ref_clk'te surulur. Full duplex varsayimi: col = 0, crs = crs_dv.
module rmii_adapter (
    input  wire       ref_clk,      // 50 MHz (PHY REFCLK ile ayni kaynak)
    input  wire       rst_n,
    // RMII (PHY)
    input  wire [1:0] rmii_rxd,
    input  wire       rmii_crs_dv,
    input  wire       rmii_rx_er,
    output reg  [1:0] rmii_txd,      // ref_clk DUSEN kenarinda surulur: PHY yukselen kenarda ornekler
    output reg        rmii_tx_en,    // (LAN8720A tsu 4 ns / th 1.5 ns), her iki yonde ~10 ns pay
    // MII (MAC = AXI EthernetLite)
    (* X_INTERFACE_PARAMETER = "FREQ_HZ 25000000" *)
    output wire       mii_rx_clk,
    output reg  [3:0] mii_rxd,
    output reg        mii_rx_dv,
    output reg        mii_rx_er,
    (* X_INTERFACE_PARAMETER = "FREQ_HZ 25000000" *)
    output wire       mii_tx_clk,
    input  wire [3:0] mii_txd,
    input  wire       mii_tx_en,
    output reg        mii_crs,
    output wire       mii_col
);
    // --- 25 MHz MII saati (ref_clk / 2) -----------------------------------------------------
    reg clk25_reg = 1'b0;
    always @(posedge ref_clk) begin
        clk25_reg <= ~clk25_reg;
    end
    wire clk25;
    BUFG bufg_clk25 (.I(clk25_reg), .O(clk25));
    assign mii_rx_clk = clk25;
    assign mii_tx_clk = clk25;
    assign mii_col    = 1'b0;

    // ref_clk posedge'inde clk25_reg==1 ise bu kenarda clk25 DUSER (1->0): MAC bu kenarda
    // ornekleme yapmaz, cikislarini bir onceki yukselen kenarda degistirmistir -> MII giris
    // orneklemek ve MII cikis guncellemek icin guvenli an.
    wire clk25_falls = clk25_reg;

    // --- RX: PHY dibitlerini kaydet -----------------------------------------------------------
    reg [1:0] rxd_q;
    reg       crs_dv_q;
    reg       rx_er_q;
    always @(posedge ref_clk) begin
        rxd_q    <= rmii_rxd;
        crs_dv_q <= rmii_crs_dv;
        rx_er_q  <= rmii_rx_er;
    end

    // Nibble toplama + hizalama.
    reg       in_frame;     // ilk "01" gorulduginden CRS_DV dusene kadar
    reg       phase;        // 1: bu dibit nibble'in ikinci yarisi
    reg       aligned;      // SFD "11" ile hizalandi
    reg [1:0] lo_dibit;
    reg [3:0] nib_data;
    reg       nib_dv;
    reg       nib_er;
    reg       nib_toggle;   // her tamamlanan nibble'da degisir
    always @(posedge ref_clk or negedge rst_n) begin
        if (!rst_n) begin
            in_frame <= 1'b0; phase <= 1'b0; aligned <= 1'b0; lo_dibit <= 2'b00;
            nib_data <= 4'h0; nib_dv <= 1'b0; nib_er <= 1'b0; nib_toggle <= 1'b0;
        end else begin
            if (!crs_dv_q && !in_frame) begin
                phase <= 1'b0; aligned <= 1'b0;
                if (nib_dv) begin
                    nib_dv <= 1'b0; nib_toggle <= ~nib_toggle;   // cerceve sonu: DV dusuk nibble
                end
            end else if (!in_frame) begin
                // CRS_DV kalkti; preamble'in ilk "01" dibitini bekle (ondeki "00"ler atilir).
                if (rxd_q == 2'b01) begin
                    in_frame <= 1'b1; lo_dibit <= rxd_q; phase <= 1'b1;
                end
            end else begin
                if (!aligned && rxd_q == 2'b11) begin
                    // SFD'nin son dibiti: nibble'in ikinci yarisi olarak hizala.
                    nib_data <= {rxd_q, lo_dibit}; nib_dv <= 1'b1; nib_er <= rx_er_q;
                    nib_toggle <= ~nib_toggle; aligned <= 1'b1; phase <= 1'b0;
                end else if (!phase) begin
                    lo_dibit <= rxd_q; phase <= 1'b1;
                end else begin
                    nib_data <= {rxd_q, lo_dibit}; nib_er <= rx_er_q; phase <= 1'b0;
                    // RMII: cerceve sonunda CRS_DV ikinci dibitte DV'yi tasir.
                    nib_dv <= crs_dv_q; nib_toggle <= ~nib_toggle;
                    if (!crs_dv_q) begin
                        in_frame <= 1'b0; aligned <= 1'b0;
                    end
                end
            end
        end
    end

    // Nibble'i sabit MII fazina aktar: clk25'in dusen kenarinda son tamamlanan nibble'i sur
    // (nibble her 2 ref_clk'te bir tamamlanir, aktarim da 2 ref_clk'te bir: 0..1 cevrim gecikme).
    reg last_toggle;
    always @(posedge ref_clk or negedge rst_n) begin
        if (!rst_n) begin
            mii_rxd <= 4'h0; mii_rx_dv <= 1'b0; mii_rx_er <= 1'b0; last_toggle <= 1'b0; mii_crs <= 1'b0;
        end else begin
            mii_crs <= crs_dv_q;
            if (clk25_falls) begin
                if (last_toggle != nib_toggle) begin
                    mii_rxd <= nib_data; mii_rx_dv <= nib_dv; mii_rx_er <= nib_er;
                    last_toggle <= nib_toggle;
                end else begin
                    mii_rx_dv <= 1'b0; mii_rx_er <= 1'b0;
                end
            end
        end
    end

    // --- TX: MII nibble -> iki RMII dibiti -----------------------------------------------------
    // Dibitler once ref_clk yukselen kenarinda hazirlanir (tx_dibit/tx_en_r), sonra DUSEN kenarda
    // pine surulur: PHY REF_CLK'in yukselen kenarinda ornekler (LAN8720A tsu 4 ns / th 1.5 ns);
    // REF_CLK pini BUFG+yol+OBUF ile veriden birkac ns gec ciktigindan yukselen kenarda surmek
    // pay birakmaz. Dusen kenar = ~10 ns setup + ~10 ns hold (Nexys A7'de PC'ye TX dogrulandi).
    reg [3:0] tx_nib;
    reg       tx_en_q;
    reg [1:0] tx_dibit;
    reg       tx_en_r;
    always @(posedge ref_clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_nib <= 4'h0; tx_en_q <= 1'b0; tx_dibit <= 2'b00; tx_en_r <= 1'b0;
        end else begin
            if (clk25_falls) begin
                tx_nib <= mii_txd; tx_en_q <= mii_tx_en;    // MAC cikislari kararli
                tx_dibit <= mii_txd[1:0]; tx_en_r <= mii_tx_en;
            end else begin
                tx_dibit <= tx_nib[3:2]; tx_en_r <= tx_en_q;
            end
        end
    end
    always @(negedge ref_clk or negedge rst_n) begin
        if (!rst_n) begin
            rmii_txd <= 2'b00; rmii_tx_en <= 1'b0;
        end else begin
            rmii_txd <= tx_dibit; rmii_tx_en <= tx_en_r;
        end
    end
endmodule
