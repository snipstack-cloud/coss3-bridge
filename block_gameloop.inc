      [*] = ;   // === BRIDGE LOOP: episode control, game side ===
      [*] = ;   // Lives here and not in the interface actor: reading files compiles
      [*] = ;   // only on this side. The interface is reached through GUIExecuteState,
      [*] = ;   // the same way lib/miscext3.script does it.
      [*] = ;   if (plind = GetPlayerIndexInterfaceIO) and (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;   begin
      [*] = ;      var hhb : Integer = ParserSelectByKey('br_hb');
      [*] = ;      var brhblast : Integer = -1000;
      [*] = ;      if (hhb = 0) then
      [*] = ;      hhb := ParserCreate('br_hb')
      [*] = ;      else
      [*] = ;      brhblast := ParserGetIntValueByKeyByHandle(hhb, 'realtime');
      [*] = ;      var brhbnow : Integer = Round(_misc_GetRealTime);
      [*] = ;      if ((brhbnow-brhblast) >= 5) or (brhbnow < brhblast) then
      [*] = ;      begin
      [*] = ;         ParserClearByHandle(hhb);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'realtime', brhbnow);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'myplind', plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'victory', gPlayer[plind].victorystate);
      [*] = ;         ParserSaveToFileByHandle(hhb, '@@OUT@@coss3_hb.dat');
      [*] = ;      end;
      [*] = ;      var brctlpath : String = '@@OUT@@coss3_ctl.dat';
      [*] = ;      if IsFileExists(brctlpath) then
      [*] = ;      begin
      [*] = ;         var hctl : Integer = ParserSelectByKey('br_ctl');
      [*] = ;         if (hctl = 0) then
      [*] = ;         hctl := ParserCreate('br_ctl');
      [*] = ;         ParserClearByHandle(hctl);
      [*] = ;         var brctlcmd : String;       // must live outside the block below
      [*] = ;         if ParserLoadFromFileByHandle(hctl, brctlpath) then
      [*] = ;         brctlcmd := ParserGetValueByKeyByHandle(hctl, 'cmd');
      [*] = ;         DeleteFileStream(brctlpath);
      [*] = ;         var back : Integer = ParserSelectByKey('br_ack');
      [*] = ;         if (back = 0) then
      [*] = ;         back := ParserCreate('br_ack');
      [*] = ;         ParserClearByHandle(back);
      [*] = ;         ParserSetValueByKeyByHandle(back, 'cmd', brctlcmd);
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'myplind', plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'victory', gPlayer[plind].victorystate);
      [*] = ;         ParserSetValueByKeyByHandle(back, 'done', 'ping');
      [*] = ;         if (brctlcmd = 'END') then
      [*] = ;         begin
      [*] = ;            gPlayer[plind].victorystate := gc_player_victorystate_lose;
      [*] = ;            if (gPlayer[plind].victorystategametime = 0) then
      [*] = ;            gPlayer[plind].victorystategametime := GetGameTime;
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'surrendered');
      [*] = ;         end;
      [*] = ;         if (brctlcmd = 'NEW') then
      [*] = ;         begin
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'newgame_called');
      [*] = ;            ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;            GUIExecuteState('DoNewGame');
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE LOOP ===