      [*] = ;// === BRIDGE LOOP: bisection build 1 ===
      [*] = ;// DoProgress of the GUI actor runs every frame in battle and in menus.
      [*] = ;// Nothing exotic here on purpose: the loop presses the game's own
      [*] = ;// "play again" button (cTagReplay = 102 in EventEndGameStatistics),
      [*] = ;// the same way doprogress.inc:592 pokes EventModalMessage.
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
      [*] = ;if IsFileExists('@@OUT@@coss3_ctl.dat') then
      [*] = ;begin
      [*] = ;   var hctl : Integer = ParserSelectByKey('br_ctl');
      [*] = ;   if (hctl = 0) then
      [*] = ;   hctl := ParserCreate('br_ctl');
      [*] = ;   ParserClearByHandle(hctl);
      [*] = ;   var brctlcmd : String;          // must live outside the block below
      [*] = ;   var brseed0, brseed1 : Integer;
      [*] = ;   if ParserLoadFromFileByHandle(hctl, '@@OUT@@coss3_ctl.dat') then
      [*] = ;   begin
      [*] = ;      brctlcmd := ParserGetValueByKeyByHandle(hctl, 'cmd');
      [*] = ;      brseed0 := ParserGetIntValueByKeyByHandle(hctl, 'seed0');
      [*] = ;      brseed1 := ParserGetIntValueByKeyByHandle(hctl, 'seed1');
      [*] = ;   end;
      [*] = ;   DeleteFileStream('@@OUT@@coss3_ctl.dat');
      [*] = ;   var back : Integer = ParserSelectByKey('br_ack');
      [*] = ;   if (back = 0) then
      [*] = ;   back := ParserCreate('br_ack');
      [*] = ;   ParserClearByHandle(back);
      [*] = ;   ParserSetValueByKeyByHandle(back, 'cmd', brctlcmd);
      [*] = ;   ParserSetIntValueByKeyByHandle(back, 'gametime', Round(GetGameTime));
      [*] = ;   ParserSetIntValueByKeyByHandle(back, 'gamemode', gInterface.gamemode);
      [*] = ;   ParserSetIntValueByKeyByHandle(back, 'myplind', myplind);
      [*] = ;   ParserSetIntValueByKeyByHandle(back, 'victory', gPlayer[myplind].victorystate);
      [*] = ;   ParserSetValueByKeyByHandle(back, 'done', 'ping');
      [*] = ;   ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;end;
      [*] = ;// === END BRIDGE LOOP ===