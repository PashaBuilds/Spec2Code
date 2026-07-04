import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, BookOpenText, CheckCircle2, Info, Search } from "lucide-react";
import { APP_VERSION } from "@/lib/version";
import { cn } from "@/lib/utils";

/**
 * Kullanım kılavuzu — "Spec2Code'un kendi datasheet'i".
 * Datasheet-editoryal dil: numaralı bölümler, silkscreen başlıklar, bakır
 * cetveller, bus-renkli akış şemaları, scrollspy içindekiler.
 */

/* ---------- küçük yapı taşları ---------- */

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-border bg-inset px-1.5 py-0.5 font-mono text-[11px] text-text shadow-[0_1px_0_var(--border)]">
      {children}
    </kbd>
  );
}

function Callout({ tone, title, children }: { tone: "ok" | "warn" | "danger"; title: string; children: React.ReactNode }) {
  const Icon = tone === "ok" ? CheckCircle2 : tone === "warn" ? AlertTriangle : Info;
  const cls = {
    ok: "border-ok/30 bg-ok/10 [&>div>svg]:text-ok",
    warn: "border-warn/30 bg-warn/10 [&>div>svg]:text-warn",
    danger: "border-danger/30 bg-danger/10 [&>div>svg]:text-danger",
  }[tone];
  return (
    <div className={cn("my-3 rounded-md border px-3 py-2.5 text-[13px] leading-relaxed text-muted", cls)}>
      <div className="mb-1 flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" aria-hidden />
        <span className="text-silk font-mono text-[11px] font-bold text-text">{title}</span>
      </div>
      {children}
    </div>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="my-3 overflow-x-auto rounded-md border border-border border-l-2 border-l-accent bg-bg px-3 py-2.5 font-mono text-[12px] leading-relaxed text-text">
      {children}
    </pre>
  );
}

function BusTag({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className="rounded border px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase"
      style={{
        color: `var(${color})`,
        backgroundColor: `color-mix(in srgb, var(${color}) 14%, transparent)`,
        borderColor: `color-mix(in srgb, var(${color}) 45%, transparent)`,
      }}
    >
      {children}
    </span>
  );
}

function DocTable({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="my-3 overflow-x-auto rounded-md border border-border">
      <table className="w-full text-left text-[12.5px]">
        <thead>
          <tr className="border-b border-border bg-inset/70">
            {head.map((h) => (
              <th key={h} className="text-silk px-3 py-2 font-mono text-[10px] font-bold text-muted">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {rows.map((cells, i) => (
            <tr key={i}>
              {cells.map((c, j) => (
                <td key={j} className="px-3 py-2 align-top leading-relaxed text-muted">{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- akış şeması: XSA → board, PCB izi dilinde ---------- */

function PipelineDiagram() {
  const stops = [
    { x: 30, label: ".XSA", sub: "tek dosya", color: "var(--accent)" },
    { x: 175, label: "ŞEMATİK", sub: "cihaz ekle", color: "var(--bus-i2c)" },
    { x: 320, label: "GENERATE", sub: "kod + QC", color: "var(--bus-spi)" },
    { x: 465, label: "VITIS", sub: "BSP + ELF", color: "var(--bus-qspi)" },
    { x: 610, label: "BOARD", sub: "JTAG ile koş", color: "var(--ok)" },
  ];
  return (
    <div className="my-4 overflow-x-auto rounded-lg border border-border bg-bg p-4">
      <svg viewBox="0 0 740 96" className="min-w-[620px]" role="img" aria-label="Uçtan uca akış">
        {stops.slice(0, -1).map((s, i) => (
          <line
            key={i}
            x1={s.x + 100} y1={44} x2={stops[i + 1].x} y2={44}
            stroke={stops[i + 1].color} strokeWidth={2} strokeDasharray="7 5"
            className="animate-[flow-dash_0.9s_linear_infinite]"
          />
        ))}
        {stops.map((s) => (
          <g key={s.label}>
            <rect x={s.x} y={20} width={100} height={48} rx={7}
              fill="var(--chip-body)" stroke={s.color} strokeWidth={1.4} />
            <circle cx={s.x + 10} cy={30} r={2.5} fill="var(--bg)" stroke="var(--border)" />
            {[0, 1, 2].map((p) => (
              <rect key={p} x={s.x - 4} y={30 + p * 12} width={4} height={4} rx={1} fill="var(--pad)" />
            ))}
            {[0, 1, 2].map((p) => (
              <rect key={p} x={s.x + 100} y={30 + p * 12} width={4} height={4} rx={1} fill="var(--pad)" />
            ))}
            <text x={s.x + 50} y={42} textAnchor="middle" fill="var(--text)"
              fontFamily="JetBrains Mono, monospace" fontSize="12" fontWeight="700" letterSpacing="1">
              {s.label}
            </text>
            <text x={s.x + 50} y={58} textAnchor="middle" fill="var(--faint)"
              fontFamily="JetBrains Mono, monospace" fontSize="9">
              {s.sub}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function TransportDiagram() {
  const lines = [
    { y: 26, color: "var(--bus-eth)", label: "TCP / lwIP — GEM Ethernet (yalnız ZynqMP)" },
    { y: 50, color: "var(--bus-uart)", label: "Seri — PS UART / UARTLITE (COM portu)" },
    { y: 74, color: "var(--bus-can)", label: "CoreSight DCC — JTAG üzerinden (kablo yetmezse)" },
  ];
  return (
    <div className="my-4 overflow-x-auto rounded-lg border border-border bg-bg p-4">
      <svg viewBox="0 0 740 100" className="min-w-[620px]" role="img" aria-label="Transportlar">
        <rect x={16} y={14} width={128} height={72} rx={7} fill="var(--chip-body)" stroke="var(--chip-body-edge)" />
        <text x={80} y={46} textAnchor="middle" fill="var(--text)" fontFamily="JetBrains Mono, monospace" fontSize="12" fontWeight="700">HOST</text>
        <text x={80} y={62} textAnchor="middle" fill="var(--faint)" fontFamily="JetBrains Mono, monospace" fontSize="9">Spec2Code</text>
        <rect x={596} y={14} width={128} height={72} rx={7} fill="var(--chip-body)" stroke="var(--chip-body-edge)" />
        <text x={660} y={46} textAnchor="middle" fill="var(--text)" fontFamily="JetBrains Mono, monospace" fontSize="12" fontWeight="700">BOARD</text>
        <text x={660} y={62} textAnchor="middle" fill="var(--faint)" fontFamily="JetBrains Mono, monospace" fontSize="9">S2C agent</text>
        {lines.map((l) => (
          <g key={l.y}>
            <line x1={144} y1={l.y} x2={596} y2={l.y} stroke={l.color} strokeWidth={2} />
            <circle cx={144} cy={l.y} r={3} fill={l.color} />
            <circle cx={596} cy={l.y} r={3} fill={l.color} />
            <text x={370} y={l.y - 5} textAnchor="middle" fill={l.color}
              fontFamily="JetBrains Mono, monospace" fontSize="9.5">
              {l.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

/* ---------- içerik ---------- */

interface DocSection {
  id: string;
  no: string;
  title: string;
  keywords: string;
  body: React.ReactNode;
}

const P = ({ children }: { children: React.ReactNode }) => (
  <p className="my-2 max-w-3xl text-[13.5px] leading-relaxed text-muted">{children}</p>
);
const B = ({ children }: { children: React.ReactNode }) => (
  <strong className="font-semibold text-text">{children}</strong>
);
const M = ({ children }: { children: React.ReactNode }) => (
  <code className="rounded bg-inset px-1 py-0.5 font-mono text-[12px] text-accent">{children}</code>
);

const SECTIONS: DocSection[] = [
  {
    id: "genel-bakis", no: "1.0", title: "Genel bakış",
    keywords: "amaç akış pipeline nedir hızlı başlangıç",
    body: (
      <>
        <P>
          Spec2Code, kart üzerindeki entegreler için <B>deterministik sürücü kodu üretir</B>, bu kodu
          Vitis'te derleyip <B>JTAG ile karta yükler</B> ve üretilen test ajanıyla kartı{" "}
          <B>canlı olarak yoklamanı</B> sağlar. Yol boyunca hiçbir şey elle yazılmaz: tek girdi
          donanım tasarımın, tek çıktı çalışan ve ölçülebilir bir kart.
        </P>
        <PipelineDiagram />
        <P>Hızlı başlangıç — beş adım:</P>
        <DocTable head={["Adım", "Ekran", "Ne yaparsın"]} rows={[
          ["1", <M key="s">Setup</M>, <>Vivado'dan çıkan <M>.xsa</M> dosyasını sürükle (veya yolunu yapıştır) — platform ve denetleyiciler kendiliğinden algılanır.</>],
          ["2", <M key="ş">Schematic</M>, "Denetleyiciye tıkla, entegre ekle (adres / CS / mux kanalı), gerekiyorsa cihaz konfigürasyonunu düzenle."],
          ["3", <M key="g">Generate</M>, "Sürücüler + test ajanı üretilir, QC koşar; sağ kolonda kodu incele."],
          ["4", <M key="v">Vitis & Board</M>, "Workspace kur (veya mevcut olanı güncelle) → ELF; JTAG ile karta yükle."],
          ["5", <M key="t">Test Bench</M>, "Karta bağlan, operasyonları çalıştır; Bring-up ile tüm kartı tek tuşla yokla."],
        ]} />
        <Callout tone="ok" title="İPUCU">
          <Kbd>Ctrl</Kbd> + <Kbd>K</Kbd> komut paleti her ekrandan her ekrana götürür.
        </Callout>
      </>
    ),
  },
  {
    id: "tasarim-girisi", no: "2.0", title: "Donanım tasarımı girişi",
    keywords: "xsa xparameters upload platform algılama custom ip",
    body: (
      <>
        <P>
          <B>Önerilen yol tek dosyadır:</B> <M>.xsa</M>. İçindeki hardware handoff okunur; platform
          (ZynqMP / Versal / Zynq-7000 / MicroBlaze) işlemciden algılanır, PS çevre birimleri ve PL
          IP'leri adres haritasıyla şematiğe dökülür, dosyanın yolu Vitis adımına otomatik taşınır.
        </P>
        <P>
          Tanınmayan bellek-eşli IP'ler (şirket custom IP'lerin) ayrıca listelenir — bunlar sürücü
          üretimine girmez ama Vitis akışında BSP koruması otomatik uygulanır.
        </P>
        <P>
          Klasik <M>xparameters.h</M> sekmesi de durur: BSP başlığını yapıştır, aynı sonuç.
        </P>
        <Callout tone="warn" title="UYARI">
          XSA'yı yol olarak veriyorsan backend'in çalıştığı makinede erişilebilir olmalı (uygulama
          lokalde koştuğu için genelde sorun değil).
        </Callout>
      </>
    ),
  },
  {
    id: "sematik", no: "3.0", title: "Şematik",
    keywords: "schematic cihaz ekleme mux kanal adres çip led",
    body: (
      <>
        <P>
          Denetleyiciler soldadır; bir denetleyiciye tıklayıp sağ panelden entegre eklersin. I2C
          cihazlarında adres, SPI/QSPI'da chip-select, mux (TCA9548A) altındaki cihazlarda kanal
          seçilir. Çip üzerindeki <B>LED</B> descriptor durumunu gösterir: yeşil = kataloğa tanımlı,
          amber = descriptor yok.
        </P>
        <P>
          Kablolar bus rengini taşır: <BusTag color="--bus-i2c">I2C</BusTag>{" "}
          <BusTag color="--bus-spi">SPI</BusTag> <BusTag color="--bus-qspi">QSPI</BusTag>{" "}
          <BusTag color="--bus-eth">ETH</BusTag> <BusTag color="--bus-uart">UART</BusTag> — aynı renk
          dili rozetlerde ve Akış ekranında da geçerlidir. Başlıktaki <B>Canlı telemetri</B> açıkken
          son okumalar cihaz çiplerinin altında akar.
        </P>
        <P>
          Proje ve şema tarayıcıda kalıcıdır; sayfa yenilense de kaybolmaz.
        </P>
      </>
    ),
  },
  {
    id: "generate", no: "4.0", title: "Generate ve QC",
    keywords: "kod üretimi qc kalite diff dosyalar indir",
    body: (
      <>
        <P>
          <B>Generate</B> düğmesi spec'i doğrular, sürücüleri (<M>drivers/</M>), testleri ve kart
          test ajanını (<M>tests/</M>) üretir, ardından QC (stil + statik analiz) koşar. Sol kolonda
          canlı olay akışı, sağda iki sekme: <B>Üretilen kod</B> (dosya ağacı, editör, QC bulguları,
          önceki koşuma göre diff) ve <B>Vitis &amp; Board</B>.
        </P>
        <P>
          Fiziksel büyüklük okuyan tüm operasyonlar <B>mühendislik birimleriyle</B> döner: gerilimler
          mV, akımlar mA, sıcaklıklar santi-°C (2350 = 23.50 °C), nem santi-%RH, süreler saniye. Ham
          koda ihtiyaç olursa register okuması her zaman açık.
        </P>
        <Callout tone="ok" title="BİRİM POLİTİKASI">
          Dönüşüm datasheet formülüyle, tamsayı aritmetiğiyle yapılır (float yok). Shunt/sense
          direnci isteyen büyüklükler (LTC2991 current, LTC2945 power) bilinçli ham bırakılır —
          katsayı açıklamada yazar.
        </Callout>
      </>
    ),
  },
  {
    id: "vitis", no: "5.0", title: "Vitis workspace",
    keywords: "vitis xsct platform bsp elf kurulum modu güncelle custom ip",
    body: (
      <>
        <P>
          <B>Sıfırdan kur</B> modu XSA'dan platform + BSP + application üretir ve ELF'i doğrular.
          <B> Kaynakları güncelle</B> modu ise mevcut workspace'te yalnız üretilen kaynakları değiştirip
          app build alır — cihaz/konfig değişikliklerinde dakikalar kazandırır (XSA gerekmez).
        </P>
        <P>
          Custom PL IP'lerin kaynaksız sürücüleri otomatik etkisizleştirilir (BSP patch); Vitis
          Doctor bulguları ve self-heal sonuçları panelde görünür.
        </P>
        <Callout tone="warn" title="BİLİNEN MAKİNE NOTU">
          xsct'nin <M>which sdscc</M> takılması bu kurulumda stub ile çözülmüştür; farklı bir
          makinede takılma görürsen kılavuzun Sorun Giderme bölümüne bak.
        </Callout>
      </>
    ),
  },
  {
    id: "board-run", no: "6.0", title: "Board'da çalıştır (JTAG)",
    keywords: "jtag xsdb psu_init ps7_init pdi bitstream smartlynq run",
    body: (
      <>
        <P>
          Vitis &amp; Board sekmesindeki kart, ELF'i tek tuşla karta yükler. Akış platforma göre
          otomatik seçilir:
        </P>
        <DocTable head={["Platform", "Boot akışı"]} rows={[
          ["Zynq UltraScale+", <>sistem reset → <M>psu_init</M> → bitstream (varsa) → A53/R5 → ELF → çalıştır</>],
          ["Zynq-7000", <>sistem reset → <M>ps7_init</M> → bitstream → A9 → ELF → <M>ps7_post_config</M> → çalıştır</>],
          ["Versal", <><M>device program &lt;pdi&gt;</M> (PLM + PL dahil) → A72 → ELF → çalıştır</>],
        ]} />
        <P>
          JTAG bağlantısı USB kablo (lokal hw_server) veya <B>SmartLynq</B> (uzak{" "}
          <M>connect -url</M>) olabilir; XSA bit içermiyorsa <M>.bit</M> dosyası elle seçilebilir.
        </P>
        <Callout tone="danger" title="ÖNEMLİ">
          Kartın boot modu JTAG olmalı. "no targets" hatası tipik olarak kablo/güç/boot modu demektir.
        </Callout>
      </>
    ),
  },
  {
    id: "baglanti", no: "7.0", title: "Kart bağlantısı ve transportlar",
    keywords: "tcp seri coresight dcc bağlantı transport ortak kart",
    body: (
      <>
        <P>
          Tüm ekranlar (Test Bench, Akış, Bring-up, Registers, telemetri) <B>tek ortak kart
          bağlantısını</B> paylaşır — bir kez bağlanırsın, her yerde geçerlidir. Bağlantı kartı Test
          Bench ekranındadır; başlıktaki rozet durumu gösterir.
        </P>
        <TransportDiagram />
        <P>
          Transport üretilen ajanla eşleşmelidir (Setup'taki <M>Test bench transport</M> seçimi):
          Ethernet varsa lwIP TCP en hızlısıdır; yoksa PS UART; UART'a da erişim yoksa{" "}
          <B>CoreSight DCC</B> yalnız JTAG kablosuyla çalışır. Agent log seviyesi (error→debug)
          bağlantı kartından canlı değiştirilir.
        </P>
      </>
    ),
  },
  {
    id: "testbench", no: "8.0", title: "Test Bench ve Akış",
    keywords: "test bench operasyon komut akış tx rx timeline register",
    body: (
      <>
        <P>
          Test Bench, karttaki ajana S2C satır protokolüyle komut gönderir: cihaz seç → operasyon
          seç → <B>Gönder</B>. Riskli operasyonlar (yazma/init/erase) onay ister. Yanıtın ham
          satırı, ayrıştırılmış alanları ve veri baytları panelde görünür; alttaki{" "}
          <B>işlem zaman çizelgesi</B> son 60 saniyeyi çizer.
        </P>
        <P>
          <B>Akış</B> ekranı aynı bağlantının TX/RX trafiğini yönlü ve zaman damgalı listeler —
          protokol hatalarını ayıklarken birebir kayıttır. Ham konsol çıktısı içinse harici bir seri
          terminal kullan (TeraTerm/PuTTY); S2C ajanı konsol UART'ını paylaşabilir, "S2C|" ile
          başlamayan satırları yok sayar.
        </P>
      </>
    ),
  },
  {
    id: "bringup", no: "9.0", title: "Bring-up — Mission Control",
    keywords: "bringup sihirbaz doğum belgesi sertifika kategori",
    body: (
      <>
        <P>
          Tek tuşla tüm kartı yoklar: plan manifest'ten <B>bağımlılık sırasıyla</B> kurulur — güç
          izleyiciler → sensörler → saat ağacı → bellekler → RF. Her adımın LED'i canlı yanar;
          hata bir adımı durdurmaz (tam resim toplanır). Sonunda{" "}
          <B>board birth certificate</B> — yazdırılabilir tek dosyalık HTML raporu — indirilir.
        </P>
        <P>
          <M>device_init</M> adımlarını dahil et seçeneği kapatılırsa yalnız güvenli okumalar koşar.
        </P>
      </>
    ),
  },
  {
    id: "registers", no: "10.0", title: "Registers — snapshot ve diff",
    keywords: "register snapshot diff heatmap bit yazma",
    body: (
      <>
        <P>
          Cihazın register haritasını canlı okur ve <B>bit-bit ısı haritasında</B> beklenenle
          karşılaştırır: taban, datasheet reset değerleri veya önceki bir snapshot olabilir. Farklı
          bitler kırmızı yanar; bit üzerine gelince datasheet alan adı ve açıklaması görünür.
          Cihaz başına son 8 snapshot tarayıcıda saklanır.
        </P>
        <P>
          Register <B>yazmak</B> için satırdaki kalem simgesini kullan: değeri hex gir, onayla —
          yazım sonrası aynı register geri okunarak satır yerinde doğrulanır (yalnız <M>rw</M> ve{" "}
          <M>wo</M> registerlar; PMBus word komutları gibi çok baytlı komutlar kendi
          operasyonlarından okunur). SPI parçalarında geri okumanın donanım/konfigürasyon koşulu
          sol panelde &quot;Okuma koşulu&quot; olarak gösterilir: LMK04832&apos;de veri SDIO&apos;dan ya da
          &quot;SPI readback&quot; seçilen MUX pininden, LMX2820&apos;de adanmış MUXOUT pininden
          (konfigürasyonsuz), LMX1205&apos;te MUXOUT&apos;tan otomatik (okuma sırasında kendiliğinden
          aktifleşir), LMX1204&apos;te <M>MUXOUT_SEL=1</M> (R23) yazıldıktan sonra MUXOUT&apos;tan,
          ADAR1000&apos;de <M>SDOACTIVE=1</M> (0x000 ← 0x18) ile SDO&apos;dan gelir — ilgili pin MISO&apos;ya
          bağlı olmalıdır. Aynı <M>register_read</M>/<M>register_write</M> operasyonları Test Bench
          ekranından da kullanılabilir.
        </P>
      </>
    ),
  },
  {
    id: "cli", no: "11.0", title: "Headless CLI",
    keywords: "cli komut satırı otomasyon ci build vitis-update",
    body: (
      <>
        <P>UI'sız tam boru hattı — CI ve gece koşuları için:</P>
        <Code>{`python spec2code_cli.py build --spec my.spec.json
python spec2code_cli.py build --spec my.spec.json \\
  --vitis C:\\Xilinx\\Vitis\\2023.2 --xsa board.xsa \\
  --workspace D:\\ws --temp D:\\tmp --json
# mevcut workspace'te yalniz kaynak guncelle + build:
python spec2code_cli.py build --spec my.spec.json \\
  --vitis ... --workspace ... --temp ... --vitis-update`}</Code>
        <DocTable head={["Çıkış kodu", "Anlamı"]} rows={[
          [<M key="0">0</M>, "başarı"],
          [<M key="2">2</M>, "spec geçersiz / eksik argüman"],
          [<M key="3">3</M>, "codegen veya QC hatası"],
          [<M key="4">4</M>, "Vitis workspace / ELF hatası"],
        ]} />
      </>
    ),
  },
  {
    id: "platformlar", no: "12.0", title: "Platform destek matrisi",
    keywords: "zynqmp versal zynq7000 microblaze destek",
    body: (
      <>
        <DocTable head={["Platform", "Durum", "Notlar"]} rows={[
          [<B key="z">Zynq UltraScale+</B>, <BusTag key="t" color="--ok">TAM</BusTag>, "lwIP + UART test bench, JTAG psu_init; ZCU102 ile uçtan uca doğrulandı."],
          [<B key="v">Versal</B>, <BusTag key="t" color="--ok">TAM</BusTag>, "XUartPsv ajanı, PDI ile Build&Run; VCK190 ile doğrulandı. lwIP ajanı üretilmez (UART kullanılır); OSPI/CANFD cihazları kapılı."],
          [<B key="7">Zynq-7000</B>, <BusTag key="t" color="--warn">KISMİ</BusTag>, "I2C/SPI + UART ajanı + ps7_init; zc702 ile doğrulandı. PS QSPI (XQspiPs) henüz desteklenmez — açık hata verir."],
          [<B key="m">MicroBlaze</B>, <BusTag key="t" color="--warn">SINIRLI</BusTag>, "UARTLITE ajanı + BSP/workspace (mb ELF doğrulandı); AXI IIC/SPI cihaz üretimi henüz yok — açık hata verir."],
        ]} />
        <Callout tone="ok" title="DÜRÜST KAPILAR">
          Desteklenmeyen sürücüye bağlı cihazlarda üretim, derlenemeyecek kod basmak yerine net bir
          hata mesajıyla durur.
        </Callout>
      </>
    ),
  },
  {
    id: "sorun-giderme", no: "13.0", title: "Sorun giderme",
    keywords: "hata jtag no targets parse timeout çift main port",
    body: (
      <>
        <DocTable head={["Belirti", "Muhtemel neden / çözüm"]} rows={[
          [<M key="a">no targets</M>, "JTAG'de hedef yok: kart gücü, USB-JTAG kablosu, boot modu JTAG mı?"],
          [<M key="b">request parse failed</M>, "Eski (v0.1.95 öncesi) ajan ELF'i karttadır — Generate + karta yeniden yükle."],
          [<M key="c">yanıt zaman aşımı</M>, "Transport uyumsuz olabilir (ör. ajan UART, bağlantı TCP) veya kart resetlenmiştir; bağlantı düşmez, tekrar dene."],
          [<M key="d">çift main() link hatası</M>, "Aynı workspace'te transport değiştirdiysen 'Kaynakları güncelle' bayat ajan dosyalarını temizler; en kötü ihtimalle Sıfırdan kur."],
          [<M key="e">port 8077 dolu</M>, "Uygulama bir sonraki boş portu kendisi seçer; konsol çıktısındaki adresi kullan."],
          [<M key="f">lwIP BSP hatası (update modunda)</M>, "Ethernet ajanı BSP kütüphanesi ister — bu değişiklik 'Sıfırdan kur' gerektirir."],
        ]} />
      </>
    ),
  },
  {
    id: "kisayollar", no: "14.0", title: "Kısayollar ve ipuçları",
    keywords: "klavye kısayol palet demo",
    body: (
      <>
        <DocTable head={["Kısayol / URL", "İşlev"]} rows={[
          [<span key="k"><Kbd>Ctrl</Kbd> + <Kbd>K</Kbd></span>, "Komut paleti: ekran geçişleri, Generate, karta bağlan/kes."],
          [<M key="d">?demo</M>, "Backend'siz temsili şema yükler (görsel deneme için)."],
          [<span key="e"><Kbd>Enter</Kbd> (boş)</span>, "Akış/konsol girişinde çıplak Enter, ajanın '>' canlılık istemini tetikler."],
        ]} />
        <P>
          Sürüm geçmişi için paket içindeki <M>changelog.md</M> dosyasına bakabilirsin — her sürümün
          tam dökümü oradadır.
        </P>
      </>
    ),
  },
];

/* ---------- ana bileşen ---------- */

export default function DocsPanel() {
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState(SECTIONS[0].id);
  const contentRef = useRef<HTMLDivElement | null>(null);
  // İçindekilerden tıklanınca kullanıcı elle kaydırana dek scrollspy sussun
  // (programatik smooth scroll wheel/touch üretmez).
  const spyLocked = useRef(false);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return SECTIONS;
    return SECTIONS.filter((s) =>
      (s.title + " " + s.keywords).toLowerCase().includes(needle),
    );
  }, [query]);

  // Scrollspy: görünür başlığa göre içindekileri aydınlat.
  useEffect(() => {
    const root = contentRef.current;
    if (!root) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (spyLocked.current) return;
        const hit = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (hit?.target?.id) setActiveId(hit.target.id);
      },
      { root, rootMargin: "0px 0px -70% 0px", threshold: 0 },
    );
    for (const s of SECTIONS) {
      const el = root.querySelector(`#${s.id}`);
      if (el) observer.observe(el);
    }
    // Son bölümler viewport'tan kısa kaldığında başlıkları üst %30'a hiç
    // giremez; elle dibe inildiğinde son bölümü aydınlat.
    const onScroll = () => {
      if (spyLocked.current) return;
      if (root.scrollTop < root.scrollHeight - root.clientHeight - 2) return;
      setActiveId(SECTIONS[SECTIONS.length - 1].id);
    };
    const unlock = () => {
      spyLocked.current = false;
    };
    root.addEventListener("scroll", onScroll, { passive: true });
    root.addEventListener("wheel", unlock, { passive: true });
    root.addEventListener("touchmove", unlock, { passive: true });
    root.addEventListener("keydown", unlock);
    return () => {
      observer.disconnect();
      root.removeEventListener("scroll", onScroll);
      root.removeEventListener("wheel", unlock);
      root.removeEventListener("touchmove", unlock);
      root.removeEventListener("keydown", unlock);
    };
  }, [visible.length]);

  function jump(id: string) {
    setActiveId(id);
    spyLocked.current = true;
    contentRef.current?.querySelector(`#${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[248px_minmax(0,1fr)]">
      {/* içindekiler */}
      <aside className="hidden min-h-0 flex-col overflow-hidden rounded-lg border border-border bg-elev lg:flex">
        <div className="border-b border-border px-3 py-3">
          <div className="mb-2 flex items-center gap-2">
            <BookOpenText className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-silk font-mono text-xs font-bold text-text">KULLANIM KILAVUZU</span>
          </div>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2 top-2 h-3.5 w-3.5 text-faint" aria-hidden />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="bölüm ara..."
              className="h-8 w-full rounded-md border border-border bg-inset pl-7 pr-2 font-mono text-[11px] text-text placeholder:text-faint focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
            />
          </div>
        </div>
        <nav className="min-h-0 flex-1 overflow-auto py-2">
          {visible.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => jump(s.id)}
              className={cn(
                "group flex w-full items-baseline gap-2 border-l-2 px-3 py-1.5 text-left transition-colors",
                activeId === s.id
                  ? "border-l-accent bg-accent-dim/40 text-text"
                  : "border-l-transparent text-muted hover:text-text",
              )}
            >
              <span className={cn(
                "shrink-0 font-mono text-[10px]",
                activeId === s.id ? "text-accent" : "text-faint",
              )}>
                {s.no}
              </span>
              <span className="text-[12.5px] leading-snug">{s.title}</span>
            </button>
          ))}
          {visible.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-faint">Eşleşen bölüm yok.</p>
          )}
        </nav>
        <div className="border-t border-border px-3 py-2">
          <p className="font-mono text-[9.5px] leading-relaxed text-faint">
            SPEC2CODE FIELD MANUAL · şematikten çalışan karta
          </p>
        </div>
      </aside>

      {/* içerik */}
      <div ref={contentRef} className="min-h-0 overflow-auto rounded-lg border border-border bg-elev">
        {/* kapak */}
        <header className="relative overflow-hidden border-b border-border px-6 py-8">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.35]"
            style={{
              backgroundImage:
                "radial-gradient(color-mix(in srgb, var(--accent) 22%, transparent) 1px, transparent 1px)",
              backgroundSize: "22px 22px",
            }}
          />
          <div className="relative">
            <p className="text-silk mb-1 font-mono text-[10px] font-bold text-accent">
              REV {APP_VERSION} · SAHA EL KİTABI
            </p>
            <h1 className="font-mono text-2xl font-bold tracking-tight text-text">
              Spec2Code Kullanım Kılavuzu
            </h1>
            <p className="mt-2 max-w-2xl text-[13.5px] leading-relaxed text-muted">
              Donanım tasarımından çalışan karta giden yolun tamamı: kod üretimi, Vitis, JTAG,
              canlı test ve bring-up. Soldaki içindekilerden gez ya da bölüm ara.
            </p>
          </div>
        </header>

        {visible.map((s, i) => (
          <section
            key={s.id}
            id={s.id}
            className="scroll-mt-4 border-b border-border/60 px-6 py-6 animate-fade-in"
            style={{ animationDelay: `${Math.min(i * 45, 360)}ms`, animationFillMode: "backwards" }}
          >
            <div className="mb-3 flex items-baseline gap-3">
              <span className="font-mono text-sm font-bold text-accent">{s.no}</span>
              <h2 className="text-silk font-mono text-[15px] font-bold text-text">{s.title}</h2>
              <span className="h-px flex-1 bg-gradient-to-r from-accent/50 to-transparent" aria-hidden />
            </div>
            {s.body}
          </section>
        ))}

        <footer className="px-6 py-6">
          <p className="font-mono text-[10px] text-faint">
            · · · kılavuzun sonu — kartın ilk nefesi hayırlı olsun · · ·
          </p>
        </footer>
      </div>
    </div>
  );
}
