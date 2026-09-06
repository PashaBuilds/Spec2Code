# Surucu struct API'si + ust seviye CIT + Xilinx-seviyesi simulasyon (2026-09-06)

Kullanici karari (2026-09-06): "driver katmaninda Xilinx API'lari cagrilmali; driver ham
voltaj/durum bilgisini struct olarak vermeli; cit/ klasoru kalsin ama bir UST seviye olsun
(hangi voltajlarin okunacagini bilir, OK/NOK'u anlamlandirir); cit de tests de surucu
fonksiyonlariyla bilgiye erissin; kullaniciya `spec2code_` adli dosya gitmesin; geriye
donuk uyumluluk onemli degil; ilk denemeler Nexys A7 kartinda."

## Katmanlar (yukaridan asagiya, tek yonlu bagimlilik)

```
tests/  (test bench ajani, self-test, tests/sim/*)      -- spec2code_* adlari BURADA
cit/    (S<Mod>Cit: surucu struct'larini anlamlandirir)  -- surucuyu cagirir
drivers/ (S<Mod>Status, S<Mod>Voltage..., Xilinx API)    -- kullaniciya giden katman
Xilinx BSP
```

## drivers/<mod>.h (kullaniciya gider; `spec2code_` yok)

* Dizi donuslu op (`returns: voltages[8]`): `typedef struct { unsigned short usArrVoltage[8]; } SLtc2991Voltage;`
  ve `int ltc2991VoltageRead(handle, SLtc2991Voltage* spVoltage);` (isim: returns adinin tekili).
* Durum registerleri (fields tanimli, width<=16, `access: ro` VEYA `post_init_status.reg`):
  `SLtc2991Status { unsigned int uiV1Ready:1; ...; unsigned char ucStatusLow; ... }` ve
  `int ltc2991StatusRegistersRead(handle, SLtc2991Status* spStatus);` (bitler descriptor
  bit tanimlariyla birebir, ham bayt da yaninda).
* Skaler op'lar degismez (`int*`, `unsigned short*`...).
* `drivers/dbg_printf.h/.c` (v0.1.169): `dbg_printf(DEBUG_LEVEL_x, fmt, ...)`, seviyeler
  ALWAYS 0 / ERROR 1 / WARNING 2 / MSG 3 / INFO 4 / TRACE 5, esik calisma zamaninda
  (`dbgLevelSet`, varsayilan ERROR; yalniz esikten kucuk/esit basilir). Bus izleri
  `dbgTraceI2c/Spi` (TRACE), bus hatalari `TRACEERR|...` (ERROR). Test bench `dbgSinkSet` ile
  satiri S2C-LOG cercevesine sarar; tek basina xil_printf. (bus_trace.h kaldirildi.)

## cit/<mod>_cit.h (ust seviye; surucu uzerinde)

* `S<Mod>CitLimit`: olcum basina `{iMin, iMax, uiLimitVar, uiEtkin}` (kapali aralik, min == max gecerli; kritik/uyari yok); varsayilan
  spec `config.cit.measurements` (kanal bazli), `<MOD>_CIT_LIMIT_VARSAYILAN`.
* `S<Mod>Cit`: `sBayraklar` (op okuma-basari bitleri + olcum basina OK biti = okundu VE
  limit icinde), `S<Mod>Status sDurum`, olcum struct/alanlari (surucu tipleriyle),
  `uiHataSayac`, `uiNokSayac`.
* `<mod>CitInit(handle)` = surucu `DeviceInit`; `<mod>CitRead(handle, const S<Mod>CitLimit*,
  S<Mod>Cit*)`: surucu fonksiyonlarini cagirir, sonra anlamlandirir.
* `cit/sistem_cit.*`: `SSistemCitBus` (denetleyici handle'lari), `SSistemCitLimit`,
  `SSistemCit`; `sistemCitInit/Read`.
* cit/hal/ (HAL sarmalayici) ve cit/sim/ KALDIRILDI.

## Simulasyon (tests/sim/, yalniz test bench derlemesi)

* `tests/sim/spec2code_sim_xilinx.h`: `-include` ile derlemeye giren makro araya-girme
  basligi: `XIic_DynSend/DynRecv/Send/Recv`, `XIicPs_MasterSendPolled/RecvPolled`,
  `XSpi_SetSlaveSelect/Transfer`, `XSpiPs_SetSlaveSelect/PolledTransfer` ->
  `spec2codeSim*` sarmalayicilari. Sarmalayici adres/CS'i sanal cihaz zincirinde bulursa
  simulatoru kosturur, bulamazsa GERCEK Xilinx fonksiyonunu cagirir (karisik mod).
* `tests/sim/spec2code_sim.h/.c`: sanal cihaz kaydi (`SSpec2codeSimI2cCihaz`, `...SpiCihaz`,
  `spec2codeSimI2cEkle`, `spec2codeSimSpiEkle`), sanal TCA9548A switch.
* `tests/sim/<mod>_sim.*`: register-dosyasi simulatorleri (eski cit/sim; davranis bloklari
  ayni). Test bench ajani `simulate` isaretli cihazlari acilista kaydeder
  (`spec2codeSimHazirla`); dispatch dogrudan GERCEK surucuyu cagirir - sarmalayici yok.
* Vitis: sim klasoru varsa `app config -add compiler-misc "-include spec2code_sim_xilinx.h"`
  + include-path. Kullanici firmware'inde surucu saf kalir.
* Host testi: Xilinx stub basliklari + interposer ile drivers+cit+sim gcc'de kosar.
