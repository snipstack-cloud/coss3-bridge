      [*] = ;   // === BRIDGE ENDGAME: episode control, interface side ===
      [*] = ;   // Why here and not in Progress. When a match ends the engine pauses the
      [*] = ;   // simulation: doprogress.inc sees victorystate<>none, calls
      [*] = ;   // SetProgressingPauseMode(True) and shows the EndGame dialog. Everything
      [*] = ;   // that lives in Progress freezes with it - including the old episode loop.
      [*] = ;   // So the bridge could neither see the defeat nor start the next match: the
      [*] = ;   // trace just stopped and the policy guessed at three possible causes.
      [*] = ;   // DoProgress of the interface actor keeps running through that pause and
      [*] = ;   // through the main menu, which is exactly what episode control needs.
      [*] = ;   // Reading files compiles here: shownews.inc uses the same IsFileExists and
      [*] = ;   // ParserLoadFromFileByHandle. The comment in block_gameloop claiming
      [*] = ;   // otherwise was wrong.
      [*] = ;   var brepind : Integer = -1;
      [*] = ;   var brephnd : Integer = GetPlayerHandleInterfaceIO;
      [*] = ;   if (brephnd <> 0) then
      [*] = ;   brepind := GetPlayerIndexByHandle(brephnd);
      [*] = ;   // The outcome goes out as a WORD, not as a number. gc_player_victorystate_*
      [*] = ;   // are engine constants: their values are not in the scripts, so a number
      [*] = ;   // written here would be a number nobody on the python side could read.
      [*] = ;   var brevic : String = 'none';
      [*] = ;   if (brepind >= 0) and (brepind < gc_MaxPlayerCount) then
      [*] = ;   begin
      [*] = ;      if (gPlayer[brepind].victorystate = gc_player_victorystate_win) then
      [*] = ;      brevic := 'win'
      [*] = ;      else
      [*] = ;      if (gPlayer[brepind].victorystate = gc_player_victorystate_lose) then
      [*] = ;      brevic := 'lose';
      [*] = ;   end;
      [*] = ;   // Interface heartbeat. Separate file from coss3_hb.dat on purpose: that one
      [*] = ;   // proves the Progress tick is alive, this one proves the interface is - and
      [*] = ;   // the whole point is that these two stop at different moments.
      [*] = ;   var brehb : Integer = ParserSelectByKey('br_gui');
      [*] = ;   var brelast : Integer = -1000;
      [*] = ;   if (brehb = 0) then
      [*] = ;   brehb := ParserCreate('br_gui')
      [*] = ;   else
      [*] = ;   brelast := ParserGetIntValueByKeyByHandle(brehb, 'realtime');
      [*] = ;   var brenow : Integer = Round(_misc_GetRealTime);
      [*] = ;   if ((brenow-brelast) >= 2) or (brenow < brelast) then
      [*] = ;   begin
      [*] = ;      ParserClearByHandle(brehb);
      [*] = ;      ParserSetIntValueByKeyByHandle(brehb, 'realtime', brenow);
      [*] = ;      ParserSetIntValueByKeyByHandle(brehb, 'gametime', Round(GetGameTime));
      [*] = ;      ParserSetIntValueByKeyByHandle(brehb, 'myplind', brepind);
      [*] = ;      ParserSetIntValueByKeyByHandle(brehb, 'gamemode', gInterface.gamemode);
      [*] = ;      ParserSetValueByKeyByHandle(brehb, 'victory', brevic);
      [*] = ;      if (GetProgressingPauseMode) then
      [*] = ;      ParserSetValueByKeyByHandle(brehb, 'paused', 'yes')
      [*] = ;      else
      [*] = ;      ParserSetValueByKeyByHandle(brehb, 'paused', 'no');
      [*] = ;      ParserSaveToFileByHandle(brehb, '@@OUT@@coss3_gui.dat');
      [*] = ;   end;
      [*] = ;   // Commands are read here ONLY when the match is already over. While it runs,
      [*] = ;   // the block in Progress owns coss3_ctl.dat, exactly as before - the two
      [*] = ;   // conditions are disjoint, so the file has one reader at any moment and
      [*] = ;   // nothing that works today changes.
      [*] = ;   if (brevic <> 'none') and IsFileExists('@@OUT@@coss3_ctl.dat') then
      [*] = ;   begin
      [*] = ;      var brectl : Integer = ParserSelectByKey('br_ctl');
      [*] = ;      if (brectl = 0) then
      [*] = ;      brectl := ParserCreate('br_ctl');
      [*] = ;      ParserClearByHandle(brectl);
      [*] = ;      var brecmd : String;          // must live outside the block below
      [*] = ;      if ParserLoadFromFileByHandle(brectl, '@@OUT@@coss3_ctl.dat') then
      [*] = ;      brecmd := ParserGetValueByKeyByHandle(brectl, 'cmd');
      [*] = ;      DeleteFileStream('@@OUT@@coss3_ctl.dat');
      [*] = ;      var breack : Integer = ParserSelectByKey('br_ack');
      [*] = ;      if (breack = 0) then
      [*] = ;      breack := ParserCreate('br_ack');
      [*] = ;      ParserClearByHandle(breack);
      [*] = ;      ParserSetValueByKeyByHandle(breack, 'cmd', brecmd);
      [*] = ;      ParserSetValueByKeyByHandle(breack, 'from', 'endgame');
      [*] = ;      ParserSetValueByKeyByHandle(breack, 'victory', brevic);
      [*] = ;      ParserSetIntValueByKeyByHandle(breack, 'gametime', Round(GetGameTime));
      [*] = ;      ParserSetIntValueByKeyByHandle(breack, 'myplind', brepind);
      [*] = ;      ParserSetValueByKeyByHandle(breack, 'done', 'ping');
      [*] = ;      if (brecmd = 'NEW') then
      [*] = ;      begin
      [*] = ;         // Match settings are NOT re-applied here. _player_ResetAllPlayers
      [*] = ;         // clears gPlayer, while the conditions live in gMap.settings and
      [*] = ;         // gMap.players - the previous NEW put them there and nothing between
      [*] = ;         // matches touches them. They are REPORTED instead, so that 'carried
      [*] = ;         // over' stays distinguishable from 'silently changed': on 13.09 the
      [*] = ;         // same ack fields were the only way to tell one from the other.
      [*] = ;         ParserSetIntValueByKeyByHandle(breack, 'res', gMap.settings.gen.resourcestart);
      [*] = ;         ParserSetIntValueByKeyByHandle(breack, 'peace', gMap.settings.additional.peacetime);
      [*] = ;         ParserSetIntValueByKeyByHandle(breack, 'nat0', gMap.players[0].cid);
      [*] = ;         ParserSetIntValueByKeyByHandle(breack, 'nat1', gMap.players[1].cid);
      [*] = ;         ParserSetIntValueByKeyByHandle(breack, 'ai1', gMap.players[1].aidifficulty);
      [*] = ;         ParserSetValueByKeyByHandle(breack, 'done', 'restarted_after_end');
      [*] = ;         ParserSaveToFileByHandle(breack, '@@OUT@@coss3_ack.dat');
      [*] = ;         // The engine's own 'play again' recipe, taken from cTagReplay in
      [*] = ;         // eventendgamestatistics.inc, plus the two things that button does not
      [*] = ;         // need and we do: the EndGame dialog is on screen and the simulation
      [*] = ;         // is paused. Without hiding the dialog doprogress puts the pause back
      [*] = ;         // on the very next frame (its else-branch re-shows EndGame).
      [*] = ;         _gui_SetGUIElementVisibleByName('EndGame', False);
      [*] = ;         _player_ResetAllPlayers;
      [*] = ;         gbool_gui_maxcameradist := True;
      [*] = ;         // False = a fresh map key. True would replay the same map, which is
      [*] = ;         // what cTagReplay does; make it a separate command when we want it.
      [*] = ;         gbool_gui_donewgamerestart := False;
      [*] = ;         SetProgressingPauseMode(False);
      [*] = ;         ExecuteState('DoNewGame');
      [*] = ;      end;
      [*] = ;      ParserSaveToFileByHandle(breack, '@@OUT@@coss3_ack.dat');
      [*] = ;   end;
      [*] = ;   // === END BRIDGE ENDGAME ===
