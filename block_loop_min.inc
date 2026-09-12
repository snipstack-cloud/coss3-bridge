      [*] = ;// === BRIDGE LOOP: heartbeat probe, no handshake, no engine calls ===
      [*] = ;// Bisection build. Writes coss3_hb.dat every ~5 real seconds while the
      [*] = ;// game runs. If the file never appears, the injection point itself is
      [*] = ;// dead - not the NEW/END logic.
      [*] = ;var hhb : Integer = ParserSelectByKey('br_hb');
      [*] = ;var brhblast : Integer = -1000;
      [*] = ;if (hhb = 0) then
      [*] = ;hhb := ParserCreate('br_hb')
      [*] = ;else
      [*] = ;brhblast := ParserGetIntValueByKeyByHandle(hhb, 'realtime');
      [*] = ;var brhbnow : Integer = Round(_misc_GetRealTime);
      [*] = ;if ((brhbnow-brhblast) >= 5) or (brhbnow < brhblast) then
      [*] = ;begin
      [*] = ;   ParserClearByHandle(hhb);
      [*] = ;   ParserSetIntValueByKeyByHandle(hhb, 'realtime', brhbnow);
      [*] = ;   ParserSetIntValueByKeyByHandle(hhb, 'gametime', Round(GetGameTime));
      [*] = ;   ParserSetIntValueByKeyByHandle(hhb, 'gamemode', gInterface.gamemode);
      [*] = ;   ParserSetIntValueByKeyByHandle(hhb, 'myplind', myplind);
      [*] = ;   ParserSaveToFileByHandle(hhb, '@@OUT@@coss3_hb.dat');
      [*] = ;end;
      [*] = ;// === END BRIDGE LOOP ===