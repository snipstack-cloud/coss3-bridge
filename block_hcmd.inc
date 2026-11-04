      [*] = ;   // === BRIDGE HUMAN COMMANDS: the bot plays the human side itself ===
      [*] = ;   // Same command file as the AI-side bridge (coss3_cmd_P<n>.dat), same numbers,
      [*] = ;   // so everything above the bridge - model, prompts, logs, replay - is unchanged.
      [*] = ;   // What changes is who executes: instead of dropping an idea into the native AI
      [*] = ;   // queue we call the engine directly, exactly as the game does for a human.
      [*] = ;   if (gPlayer[plind].bexists) and (not gPlayer[plind].bai) and
      [*] = ;      (not _net_IsClient) and (not _net_IsReplay) and
      [*] = ;      (gMap.gamestage = gc_map_gamestage_started) then
      [*] = ;   begin
      [*] = ;      // The game writes no log at all unless asked: cossacks.ini ships with
      [*] = ;      // LogFileEnabled=false, and every bridge: line we ever wrote went nowhere.
      [*] = ;      // Turn it on from here, once per session - no ini editing, reversible, and
      [*] = ;      // it costs nothing but a boolean. Without this there is no bot action log.
      [*] = ;      // Why a command failed must reach the MODEL, not just the log. Left in the
      [*] = ;      // dark it invents a reason: on the mock it decided within a minute that
      [*] = ;      // buildings cost food. The state block picks this up next tick.
      [*] = ;      var hfl : Integer = ParserSelectByKey('br_hfail');
      [*] = ;      if (hfl = 0) then
      [*] = ;      hfl := ParserCreate('br_hfail');
      [*] = ;      var hlg : Integer = ParserSelectByKey('br_hlog');
      [*] = ;      if (hlg = 0) then
      [*] = ;      begin
      [*] = ;         hlg := ParserCreate('br_hlog');
      [*] = ;         if (not GetLogFileEnabled) then
      [*] = ;         SetLogFileEnabled(True);
      [*] = ;         Log('bridge-human: log enabled, human-slot bot is live for P' + IntToStr(plind));
      [*] = ;      end;
      [*] = ;      var hcpath : String = '@@OUT@@coss3_cmd_P' + IntToStr(plind) + '.dat';
      [*] = ;      // OPENING (1.11, mac, player's word): the player places the town hall and the mill 2-3 s after load; the bot did it at
      [*] = ;      // 13-14 s, because the launcher starts python only after NEW is acked and game time runs. Python now leaves
      [*] = ;      // coss3_open_P<n>.dat BEFORE NEW - an ordinary command batch (BUILDERS 12, BUILD center, BUILD mill) - and this block
      [*] = ;      // takes it on the first tick of the game: no command file pending, game time under 10 s, no town hall of ours yet.
      [*] = ;      // Used once and deleted, aloud. A town hall already standing (a start with buildings) - the file is removed unused.
      [*] = ;      var hopath : String = '@@OUT@@coss3_open_P' + IntToStr(plind) + '.dat';
      [*] = ;      var hcopen : Boolean = False;
      [*] = ;      if (not IsFileExists(hcpath)) and (GetGameTime < 10) then
      [*] = ;      if IsFileExists(hopath) then
      [*] = ;      begin
      [*] = ;         var hoph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;         var hon : Integer = GetPlayerGameObjectsCountByHandle(hoph);
      [*] = ;         var hocen : Boolean = False;
      [*] = ;         var hok : Integer;
      [*] = ;         for hok := 0 to hon-1 do
      [*] = ;         begin
      [*] = ;            var hopo : Pointer = _unit_GetTObj(GetGameObjectHandleByIndex(hok, hoph));
      [*] = ;            if (hopo<>nil) then
      [*] = ;            if (gObjProp[TObj(hopo).cid][TObj(hopo).id].airole = gc_ai_unit_center) then hocen := True;
      [*] = ;         end;
      [*] = ;         if (hocen) then
      [*] = ;         begin
      [*] = ;            DeleteFileStream(hopath);
      [*] = ;            Log('bridge-human: OPENING skipped for P' + IntToStr(plind) + ' - a town hall already stands, file removed');
      [*] = ;         end
      [*] = ;         else
      [*] = ;         hcopen := True;
      [*] = ;      end;
      [*] = ;      if (IsFileExists(hcpath)) or (hcopen) then
      [*] = ;      begin
      [*] = ;         var hch : Integer = ParserSelectByKey('br_hcmd');
      [*] = ;         if (hch = 0) then
      [*] = ;         hch := ParserCreate('br_hcmd');
      [*] = ;         ParserClearByHandle(hch);
      [*] = ;         var hcok : Boolean = False;
      [*] = ;         if (hcopen) then
      [*] = ;         begin
      [*] = ;            hcok := ParserLoadFromFileByHandle(hch, hopath);
      [*] = ;            DeleteFileStream(hopath);
      [*] = ;            Log('bridge-human: OPENING at ' + FloatToStr(GetGameTime) + ' s for P' + IntToStr(plind) + ' from coss3_open_P' + IntToStr(plind) + '.dat');
      [*] = ;         end
      [*] = ;         else
      [*] = ;         begin
      [*] = ;            hcok := ParserLoadFromFileByHandle(hch, hcpath);
      [*] = ;            DeleteFileStream(hcpath);
      [*] = ;         end;
      [*] = ;         if (hcok) then
      [*] = ;         begin
      [*] = ;            // A new batch of commands - the old failure reason has been read.
      [*] = ;            // Cleared HERE, not on state write: the state is written every
      [*] = ;            // second and the model reads it every fifteen.
      [*] = ;            // Every refusal in the batch is APPENDED with ' | ', not written over.
      [*] = ;            // 18.09 (mac): BUILD mill was refused for 'no peasants' and TRAIN
      [*] = ;            // peasant failed right after it in the same tick - the second reason
      [*] = ;            // overwrote the first, the model saw only TRAIN and lost two ticks
      [*] = ;            // guessing why the mill did not start. Three times per game.
      [*] = ;            // Python strips the leading separator.
      [*] = ;            ParserSetValueByKeyByHandle(hfl, 'why', '');
      [*] = ;            var hccid : Integer = gPlayer[plind].cid;
      [*] = ;            var hcph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var hccount : Integer = ParserGetIntValueByKeyByHandle(hch, 'count');
      [*] = ;            var hcn : Integer;
      [*] = ;            // Our own centre: needed as the anchor for placement and for picking
      [*] = ;            // the nearest resources. Found by scan - a human has no aidata.centerx.
      [*] = ;            var hcx, hcz : Float;
      [*] = ;            var hcbase : Integer = 0;
      [*] = ;            var hck : Integer;
      [*] = ;            var hcobjn : Integer = GetPlayerGameObjectsCountByHandle(hcph);
      [*] = ;            // FORMATION scalars at block scope (17.09 lesson: a number declared in a nested begin does not accumulate; D27 found officer 0 with officers 1 in the state).
      [*] = ;            var hfoff, hfdrum, hfr21, hfr22, hfr50, hfr51, hfdead : Integer;
      [*] = ;            for hck := 0 to hcobjn-1 do
      [*] = ;            begin
      [*] = ;               var hcgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;               var hcpo : Pointer = _unit_GetTObj(hcgo);
      [*] = ;               if (hcpo<>nil) and (hcbase = 0) then
      [*] = ;               if (gObjProp[TObj(hcpo).cid][TObj(hcpo).id].airole = gc_ai_unit_center) then
      [*] = ;               begin
      [*] = ;                  hcbase := hcgo;
      [*] = ;                  hcx := GetGameObjectPositionXByHandle(hcgo);
      [*] = ;                  hcz := GetGameObjectPositionZByHandle(hcgo);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hcbase = 0) then
      [*] = ;            begin
      [*] = ;               // No town centre yet: anchor on any object we own, usually a peasant.
      [*] = ;               if (hcobjn > 0) then
      [*] = ;               begin
      [*] = ;                  var hcany : Integer = GetGameObjectHandleByIndex(0, hcph);
      [*] = ;                  hcx := GetGameObjectPositionXByHandle(hcany);
      [*] = ;                  hcz := GetGameObjectPositionZByHandle(hcany);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // BUILDERS may arrive after BUILD in the same file, so read the cap
      [*] = ;            // first: a pre-pass costs nothing and removes an ordering trap.
      [*] = ;            var hccap : Integer = 3;
      [*] = ;            for hcn := 0 to hccount-1 do
      [*] = ;            if (ParserGetValueByKeyByHandle(hch, IntToStr(hcn) + '_cmd') = 'BUILDERS') then
      [*] = ;            begin
      [*] = ;               var hcv : Integer = ParserGetIntValueByKeyByHandle(hch, IntToStr(hcn) + '_a1');
      [*] = ;               if (hcv > 0) then
      [*] = ;               hccap := hcv;
      [*] = ;            end;
      [*] = ;            // 28.10 (mac, after game D18): targets of GROUND BALANCE in THIS file, read first like
      [*] = ;            // BUILDERS. The second pass of ground BALANCE below takes donors only from a resource
      [*] = ;            // that stands ABOVE its own target here (or has no target in the file). Before it took
      [*] = ;            // them off ANY other resource by object index, and the same men walked food -> stone ->
      [*] = ;            // food every 50 s (games D15-D18: 102, 55, 170, 52 transfers per game).
      [*] = ;            var hcbtf : Integer = -1;
      [*] = ;            var hcbtw : Integer = -1;
      [*] = ;            var hcbts : Integer = -1;
      [*] = ;            for hcn := 0 to hccount-1 do
      [*] = ;            if (ParserGetValueByKeyByHandle(hch, IntToStr(hcn) + '_cmd') = 'BALANCE') then
      [*] = ;            begin
      [*] = ;               var hcbr : Integer = ParserGetIntValueByKeyByHandle(hch, IntToStr(hcn) + '_a1');
      [*] = ;               var hcbv : Integer = ParserGetIntValueByKeyByHandle(hch, IntToStr(hcn) + '_a2');
      [*] = ;               if (hcbr = 0) and (hcbv >= 0) then
      [*] = ;               begin
      [*] = ;                  hcbtf := hcbv;
      [*] = ;               end;
      [*] = ;               if (hcbr = 1) and (hcbv >= 0) then
      [*] = ;               begin
      [*] = ;                  hcbtw := hcbv;
      [*] = ;               end;
      [*] = ;               if (hcbr = 2) and (hcbv >= 0) then
      [*] = ;               begin
      [*] = ;                  hcbts := hcbv;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // TOPUP STORE (29.10, mac, block task No1): the ground targets of THIS file are remembered (br_hbal) for the
      [*] = ;            // per-second top-up at the end of the block: idle men are seated to a resource below its target every second,
      [*] = ;            // so a peasant leaving the town hall or a finished building does not wait five seconds for python. Game D19:
      [*] = ;            // idle 4-6 from 1:15 to 1:40 while men came out one by one. Only idle men are moved - the circle fix above
      [*] = ;            // is not touched. A target of 0 is kept too: python took the men off, nobody is seated back.
      [*] = ;            var hctp : Integer = ParserSelectByKey('br_hbal');
      [*] = ;            if (hctp = 0) then
      [*] = ;            hctp := ParserCreate('br_hbal');
      [*] = ;            if (GetGameTime < ParserGetFloatValueByKeyByHandle(hctp, 'cmd' + IntToStr(plind))) then
      [*] = ;            begin
      [*] = ;               // a new game started: the targets of the old one are void
      [*] = ;               ParserSetIntValueByKeyByHandle(hctp, 'tf' + IntToStr(plind), -1);
      [*] = ;               ParserSetIntValueByKeyByHandle(hctp, 'tw' + IntToStr(plind), -1);
      [*] = ;               ParserSetIntValueByKeyByHandle(hctp, 'ts' + IntToStr(plind), -1);
      [*] = ;            end;
      [*] = ;            // 29.10 (mac, block task No1b, after balance_topup_vs_ai): the PREVIOUS targets are read before the write.
      [*] = ;            // Ground BALANCE below takes men off a resource only when python LOWERED its target, not when it repeats
      [*] = ;            // a target the sink (see TOPUP) has overfilled - otherwise the two would pull the same men every tick.
      [*] = ;            var hcof : Integer = ParserGetIntValueByKeyByHandle(hctp, 'tf' + IntToStr(plind));
      [*] = ;            var hcow : Integer = ParserGetIntValueByKeyByHandle(hctp, 'tw' + IntToStr(plind));
      [*] = ;            var hcos : Integer = ParserGetIntValueByKeyByHandle(hctp, 'ts' + IntToStr(plind));
      [*] = ;            if (ParserGetValueByKeyByHandle(hctp, 'tf' + IntToStr(plind)) = '') then
      [*] = ;            begin
      [*] = ;               hcof := -1;
      [*] = ;            end;
      [*] = ;            if (ParserGetValueByKeyByHandle(hctp, 'tw' + IntToStr(plind)) = '') then
      [*] = ;            begin
      [*] = ;               hcow := -1;
      [*] = ;            end;
      [*] = ;            if (ParserGetValueByKeyByHandle(hctp, 'ts' + IntToStr(plind)) = '') then
      [*] = ;            begin
      [*] = ;               hcos := -1;
      [*] = ;            end;
      [*] = ;            if (hcbtf >= 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hctp, 'tf' + IntToStr(plind), hcbtf);
      [*] = ;            end;
      [*] = ;            if (hcbtw >= 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hctp, 'tw' + IntToStr(plind), hcbtw);
      [*] = ;            end;
      [*] = ;            if (hcbts >= 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hctp, 'ts' + IntToStr(plind), hcbts);
      [*] = ;            end;
      [*] = ;            ParserSetFloatValueByKeyByHandle(hctp, 'cmd' + IntToStr(plind), GetGameTime);
      [*] = ;            ParserSetIntValueByKeyByHandle(hctp, 'set' + IntToStr(plind), 1);
      [*] = ;            // The targets as stored NOW (this file, else the last file): MINE takes donors from a resource above them.
      [*] = ;            var hcstf : Integer = hcbtf;
      [*] = ;            var hcstw : Integer = hcbtw;
      [*] = ;            var hcsts : Integer = hcbts;
      [*] = ;            if (hcstf < 0) then
      [*] = ;            begin
      [*] = ;               hcstf := hcof;
      [*] = ;            end;
      [*] = ;            if (hcstw < 0) then
      [*] = ;            begin
      [*] = ;               hcstw := hcow;
      [*] = ;            end;
      [*] = ;            if (hcsts < 0) then
      [*] = ;            begin
      [*] = ;               hcsts := hcos;
      [*] = ;            end;
      [*] = ;            for hcn := 0 to hccount-1 do
      [*] = ;            begin
      [*] = ;               var hckey : String = IntToStr(hcn) + '_';
      [*] = ;               var hccmd : String = ParserGetValueByKeyByHandle(hch, hckey + 'cmd');
      [*] = ;               var hca1 : Integer = ParserGetIntValueByKeyByHandle(hch, hckey + 'a1');
      [*] = ;               var hca2 : Integer = ParserGetIntValueByKeyByHandle(hch, hckey + 'a2');
      [*] = ;               // --- role -> object id. gObjProp carries airole for every object,
      [*] = ;               // so a human resolves roles exactly like the AI, without aidata. ---
      [*] = ;               var hcid : Integer = -1;
      [*] = ;               var hcj : Integer;
      [*] = ;               var hcm : Integer;          // mask of a formation type (see FORMATION below)
      [*] = ;               if (hca1 > 0) then
      [*] = ;               for hcj := 0 to gc_country_maxmembers-1 do
      [*] = ;               if (hcid < 0) and (gObjProp[hccid][hcj].airole = hca1) then
      [*] = ;               hcid := hcj;
      [*] = ;               // 4.11 (210): the archer role is first held by the diplomatic 'archerdip' (no producer), so
      [*] = ;               // TRAIN archer never reached the barracks 'archertur'. For this role only, take a non-dip member.
      [*] = ;               if (hca1 = gc_ai_unit_archer) and (hcid >= 0) then
      [*] = ;               if (StrExists(gCountry[hccid].members[hcid], 'dip')) then
      [*] = ;               for hcj := 0 to gc_country_maxmembers-1 do
      [*] = ;               if (gObjProp[hccid][hcj].airole = hca1) and (not StrExists(gCountry[hccid].members[hcj], 'dip')) then
      [*] = ;               hcid := hcj;
      [*] = ;               // A role this nation has no object for used to vanish here without
      [*] = ;               // a trace, and from the Python side that is indistinguishable from
      [*] = ;               // 'not enough resources'. Say it out loud instead.
      [*] = ;               if (hcid < 0) and (hca1 > 0) then
      [*] = ;               if (hccmd = 'BUILD') or (hccmd = 'TRAIN') then
      [*] = ;               begin
      [*] = ;                  ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + hccmd + ' role' +
      [*] = ;                       IntToStr(hca1) + ': this nation has no such object');
      [*] = ;                  Log('bridge-human: ' + hccmd + ' role' + IntToStr(hca1) +
      [*] = ;                      ' - no such object for this nation');
      [*] = ;               end;
      [*] = ;               if (hccmd = 'BUILD') and (hcid >= 0) then
      [*] = ;               begin
      [*] = ;                  var hcsid : String = gCountry[hccid].members[hcid];
      [*] = ;                  // Do we already have enough of these? BUILD is declarative.
      [*] = ;                  var hchave : Integer;
      [*] = ;                  var hcunf : Integer = 0;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hpo : Pointer = _unit_GetTObj(hgo);
      [*] = ;                     if (hpo<>nil) and (TObj(hpo).cid = hccid) and (TObj(hpo).id = hcid) then
      [*] = ;                     begin
      [*] = ;                        hchave := hchave + 1;
      [*] = ;                        if (hcunf = 0) and (not TObj(hpo).bbuilt) then
      [*] = ;                        hcunf := hgo;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  // A LAID FOUNDATION COUNTS INTO hchave, so a declarative BUILD already
      [*] = ;                  // satisfied by a 0% pit did nothing at all. Live game 4.10 against the
      [*] = ;                  // impossible AI: the gold mine stood at 0% from 2:14 to 6:11 with 26
      [*] = ;                  // peasants, 542 wood and 460 stone free, on_build 0 the whole time; gold
      [*] = ;                  // fell to 1 at 5:05 and stayed there, no upgrades, no mercenaries. The
      [*] = ;                  // engine crews a project ONCE, at laying - _ai_CallPeasantsToBuildProject
      [*] = ;                  // runs for its own slots only - and when that call comes up empty nobody
      [*] = ;                  // ever returns. So re-crew it here: the target carries the engine's own
      [*] = ;                  // stolist, the very list _unit_OrderBuild reads to decide whether a build
      [*] = ;                  // point is taken.
      [*] = ;                  //
      [*] = ;                  // 10.10: THE CREW IS CAPPED BY BUILD POINTS, NOT BY OUR WISH. Until now this
      [*] = ;                  // branch fired only when NOBODY was on the site (hcbz <= 0). Live game 10.10
      [*] = ;                  // against the player: barracks 2 was paid at 8:45 and finished at 11:15 - two
      [*] = ;                  // and a half minutes built by ONE man, while 9-10 peasants stood idle next to
      [*] = ;                  // it and this branch logged 'sent 5 workers back' four ticks in a row with
      [*] = ;                  // nobody arriving. The engine explains both. A site has a fixed number of
      [*] = ;                  // builder points PER BUILDING TYPE (gCustomObjPoints[cid][id].builderCount),
      [*] = ;                  // and _unit_OrderBuild gives a man a point only when that point is IN HIS
      [*] = ;                  // REGION (unit.script:9313) and not already occupied by someone acting
      [*] = ;                  // 'build' (:9318-9333). When no point fits, player.script:1206 keeps the man
      [*] = ;                  // ONLY for a wall (the trailing 'and gObjProp[cid][id].bwall') - for a
      [*] = ;                  // barracks he is dropped with no order at all, silently. That is why five
      [*] = ;                  // were sent and one arrived. So the crew is topped up to the FREE POINTS of
      [*] = ;                  // the site and never beyond: asking for more than the engine can seat only
      [*] = ;                  // pulls peasants off food every tick and drops them again. builderCount is
      [*] = ;                  // computed lazily by _unit_CalcBuilderPoints on the first OrderUnitsToBuild
      [*] = ;                  // for that type, so zero means 'not known yet' - then fall back to the old
      [*] = ;                  // cap and say so in the log.
      [*] = ;                  if (hchave >= hca2) and (hcunf <> 0) then
      [*] = ;                  begin
      [*] = ;                     var hcsto : Pointer = _misc_GetObjectArgData(hcunf, gc_argunit_stolist);
      [*] = ;                     var hcbz : Integer;
      [*] = ;                     if (hcsto <> nil) then
      [*] = ;                     for hck := 0 to TIntegerList(hcsto).GetCount-1 do
      [*] = ;                     begin
      [*] = ;                        var hczp : Pointer = _unit_GetTObj(TIntegerList(hcsto).Get(hck));
      [*] = ;                        if (hczp <> nil) then
      [*] = ;                        if (TObj(hczp).orders[0].itype = gc_obj_order_type_build) then
      [*] = ;                        hcbz := hcbz + 1;
      [*] = ;                     end;
      [*] = ;                     var hcup : Pointer = _unit_GetTObj(hcunf);
      [*] = ;                     var hcpts : Integer;
      [*] = ;                     if (hcup <> nil) then
      [*] = ;                     hcpts := gCustomObjPoints[TObj(hcup).cid][TObj(hcup).id].builderCount;
      [*] = ;                     var hzneed : Integer;
      [*] = ;                     if (hcpts > 0) then
      [*] = ;                     hzneed := hcpts - hcbz
      [*] = ;                     else
      [*] = ;                     hzneed := hccap - hcbz;
      [*] = ;                     if (hzneed > hccap) then
      [*] = ;                     hzneed := hccap;
      [*] = ;                     if (hzneed > 0) then
      [*] = ;                     begin
      [*] = ;                        // Same two passes as laying: idle men first, then men on the ground.
      [*] = ;                        gIntegerList.Clear;
      [*] = ;                        var hzpass : Integer;
      [*] = ;                        for hzpass := 0 to 1 do
      [*] = ;                        if (hzpass = 0) or (gIntegerList.GetCount < hzneed) then
      [*] = ;                        for hck := 0 to hcobjn-1 do
      [*] = ;                        if (gIntegerList.GetCount < hzneed) then
      [*] = ;                        begin
      [*] = ;                           var hzgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hzpo : Pointer = _unit_GetTObj(hzgo);
      [*] = ;                           if (hzpo<>nil) then
      [*] = ;                           if (gObjProp[TObj(hzpo).cid][TObj(hzpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                           if (TObj(hzpo).insideofuid = 0) then
      [*] = ;                           if ((hzpass = 1) or (TObj(hzpo).orders[0].itype = gc_obj_order_type_none)) then
      [*] = ;                           if ((hzpass = 0) or (TObj(hzpo).orders[0].itype <> gc_obj_order_type_none)) then
      [*] = ;                           if (TObj(hzpo).orders[0].itype <> gc_obj_order_type_gotomine) then
      [*] = ;                           if (TObj(hzpo).orders[0].itype <> gc_obj_order_type_build) then
      [*] = ;                           if (TObj(hzpo).orders[0].itype <> gc_obj_order_type_repair) then
      [*] = ;                           gIntegerList.Add(hzgo);
      [*] = ;                        end;
      [*] = ;                        if (gIntegerList.GetCount > 0) then
      [*] = ;                        begin
      [*] = ;                           _player_OrderUnitsToBuild(gIntegerList, hcunf, True, False, True);
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BUILD ' + hcsid +
      [*] = ;                                ': site points ' + IntToStr(hcpts) + ', building ' + IntToStr(hcbz) +
      [*] = ;                                ', sent ' + IntToStr(gIntegerList.GetCount) + ' more');
      [*] = ;                           Log('bridge-human: BUILD ' + hcsid + ' crew: points ' + IntToStr(hcpts) +
      [*] = ;                                ', on it ' + IntToStr(hcbz) + ', sent ' + IntToStr(gIntegerList.GetCount));
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  // Not enough for it? SAY SO, with the price. Until 13.09 this branch was
      [*] = ;                  // simply not taken and the bridge stayed silent: from the Python side that
      [*] = ;                  // is indistinguishable from 'the command never arrived'. The player asked
      [*] = ;                  // for mineiron=1 with 170 wood and 50 stone and saw nothing at all.
      [*] = ;                  // The price comes from the engine, so this also answers what the model could
      [*] = ;                  // never look up: what a building costs.
      [*] = ;                  if (hchave < hca2) and (not _unit_CanApplyCostByID(hccid, hcid, plind)) then
      [*] = ;                  begin
      [*] = ;                     var hcpf, hcpw, hcps, hcpg, hcpi, hcpc : Integer;
      [*] = ;                     _unit_GetCostByID(hccid, hcid, plind, hcpf, hcpw, hcps, hcpg, hcpi, hcpc);
      [*] = ;                     var hcprice : String = 'food=' + IntToStr(hcpf) + ' wood=' + IntToStr(hcpw) +
      [*] = ;                          ' stone=' + IntToStr(hcps) + ' gold=' + IntToStr(hcpg) +
      [*] = ;                          ' iron=' + IntToStr(hcpi) + ' coal=' + IntToStr(hcpc);
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BUILD ' + hcsid +
      [*] = ;                          ': NOT ENOUGH RESOURCES. It costs ' + hcprice);
      [*] = ;                     Log('bridge-human: BUILD ' + hcsid + ' - not enough resources, costs ' + hcprice);
      [*] = ;                  end;
      [*] = ;                  if (hchave < hca2) and (_unit_CanApplyCostByID(hccid, hcid, plind)) then
      [*] = ;                  begin
      [*] = ;                     // Pick a spot: rings around the base, first valid one wins.
      [*] = ;                     // The dummy is the game's own placement preview object; it is
      [*] = ;                     // destroyed right after the check and never costs anything.
      [*] = ;                     var hcmisc : Integer = GetPlayerHandleByIndex(gc_playerind_misc);
      [*] = ;                     var hcrad : Float = 4.0;
      [*] = ;                     var hcang : Integer;
      [*] = ;                     var hcfx, hcfz : Float;
      [*] = ;                     var hcfound : Boolean = False;
      [*] = ;                     // HALL AT THE FOREST LINE (3.11, player's word): pros press the first hall to the trees, or put it
      [*] = ;                     // between forest and stone, so men leaving it chop at once. The rings below take the FIRST free spot
      [*] = ;                     // around our first peasant and never look at resources. With key 'near' R (> 0) in the command, a town
      [*] = ;                     // hall tries the same rings and keeps the spot with the most wood and stone objects within R. 0 - as before.
      [*] = ;                     // Declared here, beside hcfound (a scalar declared in a nested begin does not accumulate - 17.09).
      [*] = ;                     var hcnear : Integer = ParserGetIntValueByKeyByHandle(hch, hckey + 'near');
      [*] = ;                     var hcnbest : Integer = -1;
      [*] = ;                     var hcnrad : Float = 4.0;
      [*] = ;                     var hcnang : Integer;
      [*] = ;                     var hcnok : Boolean;
      [*] = ;                     // A MINE GOES ON A DEPOSIT, so guessing by rings is the wrong tool: twelve
      [*] = ;                     // probes per ring with step 2 stand about nine units apart at radius 17, and
      [*] = ;                     // a deposit slips between them. Since 13.09 the deposit list is filled on the
      [*] = ;                     // human slot too (block_hstate calls _ai_FillOreList), so take the nearest
      [*] = ;                     // FREE one of the right kind and put the dummy straight on it. Rings below
      [*] = ;                     // stay as the fallback for everything else - and for a mine, if this misses.
      [*] = ;                     var hcuse : Integer = gObjProp[hccid][hcid].usage;
      [*] = ;                     var hcores : Integer = -1;
      [*] = ;                     if (gObjProp[hccid][hcid].airole = gc_ai_unit_minegold) then hcores := gc_resource_type_gold;
      [*] = ;                     if (gObjProp[hccid][hcid].airole = gc_ai_unit_mineiron) then hcores := gc_resource_type_iron;
      [*] = ;                     if (gObjProp[hccid][hcid].airole = gc_ai_unit_minecoal) then hcores := gc_resource_type_coal;
      [*] = ;                     if (hcores >= 0) then
      [*] = ;                     begin
      [*] = ;                        if (gPlayer[plind].aidata.orelist.GetCount = 0) then
      [*] = ;                        _ai_FillOreList(plind);
      [*] = ;                        var hcbest : Float = 1000000;
      [*] = ;                        var hcoi : Integer;
      [*] = ;                        for hcoi := 0 to gPlayer[plind].aidata.orelist.GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hcoh : Integer = gPlayer[plind].aidata.orelist.Get(hcoi);
      [*] = ;                           var hcopr : Pointer = _res_GetTRes(hcoh);
      [*] = ;                           if (hcopr<>nil) then
      [*] = ;                           if (TRes(hcopr).itype = hcores) then
      [*] = ;                           begin
      [*] = ;                              var hcox : Float = GetGameObjectPositionXByHandle(hcoh);
      [*] = ;                              var hcoz : Float = GetGameObjectPositionZByHandle(hcoh);
      [*] = ;                              var hcod : Float = VectorDistance(hcox, 0, hcoz, hcx, 0, hcz);
      [*] = ;                              if (hcod < hcbest) then
      [*] = ;                              begin
      [*] = ;                                 var hcdum2 : Integer = _player_CreateConstructionDummyBySID(hcmisc, hccid, hcsid, hcox, hcoz);
      [*] = ;                                 if (hcdum2 <> 0) then
      [*] = ;                                 begin
      [*] = ;                                    if (_misc_CanPlaceBuilding(hcdum2, plind, hcuse, hcox, hcoz, 0, 0.26, 0, -1, True)) then
      [*] = ;                                    begin
      [*] = ;                                       hcbest := hcod;
      [*] = ;                                       hcfound := True;
      [*] = ;                                       hcfx := hcox;
      [*] = ;                                       hcfz := hcoz;
      [*] = ;                                    end;
      [*] = ;                                    GameObjectDestroyByHandle(hcdum2);
      [*] = ;                                 end;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hcfound) then
      [*] = ;                        Log('bridge-human: BUILD ' + hcsid + ' on a deposit at ' + FloatToStr(hcfx) +
      [*] = ;                            ',' + FloatToStr(hcfz) + ' (' + FloatToStr(hcbest) + ' from base)');
      [*] = ;                     end;
      [*] = ;                     if (hcnear > 0) and (not hcfound) and (gObjProp[hccid][hcid].airole = gc_ai_unit_center) then
      [*] = ;                     begin
      [*] = ;                        while (hcnrad < 26.0) do
      [*] = ;                        begin
      [*] = ;                           for hcnang := 0 to 11 do
      [*] = ;                           begin
      [*] = ;                              var hcnx : Float = hcx + hcnrad * Cos(hcnang * 0.5236);
      [*] = ;                              var hcnz : Float = hcz + hcnrad * Sin(hcnang * 0.5236);
      [*] = ;                              var hcndum : Integer = _player_CreateConstructionDummyBySID(hcmisc, hccid, hcsid, hcnx, hcnz);
      [*] = ;                              if (hcndum <> 0) then
      [*] = ;                              begin
      [*] = ;                                 hcnok := _misc_CanPlaceBuilding(hcndum, plind, hcuse, hcnx, hcnz,
      [*] = ;                                      gc_path_mincoldist, 0.26, 0.5, gc_path_minemincoldist, True);
      [*] = ;                                 GameObjectDestroyByHandle(hcndum);
      [*] = ;                                 if (hcnok) then
      [*] = ;                                 begin
      [*] = ;                                    gIntegerList.Clear;
      [*] = ;                                    _misc_MakeListEnvironmentInRadius(hcnx, hcnz, hcnear, True, False, True, True, False, gIntegerList);
      [*] = ;                                    if (gIntegerList.GetCount > hcnbest) then
      [*] = ;                                    begin
      [*] = ;                                       hcnbest := gIntegerList.GetCount;
      [*] = ;                                       hcfound := True;
      [*] = ;                                       hcfx := hcnx;
      [*] = ;                                       hcfz := hcnz;
      [*] = ;                                    end;
      [*] = ;                                 end;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                           hcnrad := hcnrad + 2.0;
      [*] = ;                        end;
      [*] = ;                        gIntegerList.Clear;
      [*] = ;                        if (hcfound) then
      [*] = ;                        Log('bridge-human: BUILD ' + hcsid + ' at the forest line: ' + IntToStr(hcnbest) + ' wood and stone within ' +
      [*] = ;                            IntToStr(hcnear) + ' at ' + FloatToStr(hcfx) + ',' + FloatToStr(hcfz));
      [*] = ;                     end;
      [*] = ;                     while (hcrad < 26.0) and (not hcfound) do
      [*] = ;                     begin
      [*] = ;                        for hcang := 0 to 11 do
      [*] = ;                        if (not hcfound) then
      [*] = ;                        begin
      [*] = ;                           var hctx : Float = hcx + hcrad * Cos(hcang * 0.5236);
      [*] = ;                           var hctz : Float = hcz + hcrad * Sin(hcang * 0.5236);
      [*] = ;                           var hcdum : Integer = _player_CreateConstructionDummyBySID(hcmisc, hccid, hcsid, hctx, hctz);
      [*] = ;                           if (hcdum <> 0) then
      [*] = ;                           begin
      [*] = ;                              var hcusage : Integer = gObjProp[hccid][hcid].usage;
      [*] = ;                              var hcvalid : Boolean;
      [*] = ;                              if (hcusage = gc_obj_usage_mine) then
      [*] = ;                              hcvalid := _misc_CanPlaceBuilding(hcdum, plind, hcusage, hctx, hctz, 0, 0.26, 0, -1, True)
      [*] = ;                              else
      [*] = ;                              hcvalid := _misc_CanPlaceBuilding(hcdum, plind, hcusage, hctx, hctz,
      [*] = ;                                   gc_path_mincoldist, 0.26, 0.5, gc_path_minemincoldist, True);
      [*] = ;                              GameObjectDestroyByHandle(hcdum);
      [*] = ;                              if (hcvalid) then
      [*] = ;                              begin
      [*] = ;                                 hcfound := True;
      [*] = ;                                 hcfx := hctx;
      [*] = ;                                 hcfz := hctz;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        hcrad := hcrad + 2.0;
      [*] = ;                     end;
      [*] = ;                     if (hcfound) then
      [*] = ;                     begin
      [*] = ;                        // Builders: idle peasants first, up to the cap the model set
      [*] = ;                        // (BUILDERS command, default 3). The engine would call every
      [*] = ;                        // peasant that fits around the site and strip the mines bare.
      [*] = ;                        gIntegerList.Clear;
      [*] = ;                        // IDLE peasants first, and only then the busy ones. The
      [*] = ;                        // engine does the opposite - it grabs whoever fits around
      [*] = ;                        // the site and strips the mines bare. We already paid for
      [*] = ;                        // that lesson on the AI side; do not repeat it here.
      [*] = ;                        var hwpass : Integer;
      [*] = ;                        // Second pass tops the crew up to the cap from peasants
      [*] = ;                        // busy ON THE GROUND (food, wood, stone). It used to run
      [*] = ;                        // only when there were no idle men at all, so with one or
      [*] = ;                        // two idle the model's BUILDERS 12 gave a crew of one or
      [*] = ;                        // two: barracks 4 builders of 20, stables 2-3 of 18, three
      [*] = ;                        // series in a row (18.09). A human who picks twelve men and
      [*] = ;                        // clicks the site gets twelve. Pass 1 skips idle men (pass
      [*] = ;                        // 0 took them - no man twice), miners inside a mine, men
      [*] = ;                        // walking into one, and anyone already building.
      [*] = ;                        for hwpass := 0 to 1 do
      [*] = ;                        if (hwpass = 0) or (gIntegerList.GetCount < hccap) then
      [*] = ;                        for hck := 0 to hcobjn-1 do
      [*] = ;                        if (gIntegerList.GetCount < hccap) then
      [*] = ;                        begin
      [*] = ;                           var hwgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hwpo : Pointer = _unit_GetTObj(hwgo);
      [*] = ;                           if (hwpo<>nil) then
      [*] = ;                           if (gObjProp[TObj(hwpo).cid][TObj(hwpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                           if (TObj(hwpo).insideofuid = 0) then
      [*] = ;                           if ((hwpass = 1) or (TObj(hwpo).orders[0].itype = gc_obj_order_type_none)) then
      [*] = ;                           if ((hwpass = 0) or (TObj(hwpo).orders[0].itype <> gc_obj_order_type_none)) then
      [*] = ;                           if (TObj(hwpo).orders[0].itype <> gc_obj_order_type_gotomine) then
      [*] = ;                           // NEVER take a man off an unfinished building. The second
      [*] = ;                           // pass used to grab anyone at all, and a new foundation
      [*] = ;                           // stripped the previous one bare: in base10 (16.09) that
      [*] = ;                           // happened in 4 of the 5 stalled builds - a town hall sat
      [*] = ;                           // at 92% for twelve minutes, a mill at 59% for thirteen,
      [*] = ;                           // each losing its 3 builders on the very tick after the
      [*] = ;                           // next BUILD. Parallel building is the WINNING tactic here
      [*] = ;                           // and it is measured: three stores with one builder each
      [*] = ;                           // went up in the same 38 seconds as one. So the answer is
      [*] = ;                           // not "do not start another", it is "do not rob the one
      [*] = ;                           // already standing". Gatherers may still be taken.
      [*] = ;                           if (TObj(hwpo).orders[0].itype <> gc_obj_order_type_build) then
      [*] = ;                           if (TObj(hwpo).orders[0].itype <> gc_obj_order_type_repair) then
      [*] = ;                           gIntegerList.Add(hwgo);
      [*] = ;                        end;
      [*] = ;                        if (gIntegerList.GetCount > 0) then
      [*] = ;                        begin
      [*] = ;                           _player_ConstructBuildingList(hcph, hccid, hcsid, hcfx, hcfz, gIntegerList, True, True);
      [*] = ;                           Log('bridge-human: BUILD ' + hcsid + ' at ' + FloatToStr(hcfx) + ',' +
      [*] = ;                               FloatToStr(hcfz) + ' by ' + IntToStr(gIntegerList.GetCount) + ' workers');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BUILD ' + hcsid +
      [*] = ;                                ': nobody to build it - no peasants at all');
      [*] = ;                           Log('bridge-human: BUILD ' + hcsid + ' NO WORKERS');
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BUILD ' + hcsid +
      [*] = ;                          ': no place found within 26 around the base');
      [*] = ;                     Log('bridge-human: BUILD ' + hcsid + ' NO PLACE within 26 around base');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'TRAIN') and (hcid >= 0) then
      [*] = ;               begin
      [*] = ;                  // Producer building for this unit: the country table says which
      [*] = ;                  // building makes what. Same lookup the AI does, no aidata needed.
      [*] = ;                  var hcsid2 : String = gCountry[hccid].members[hcid];
      [*] = ;                  var hcbid : Integer = -1;
      [*] = ;                  var hci, hcjj : Integer;
      [*] = ;                  // Declared HERE, at the branch level, on purpose: a scalar declared
      [*] = ;                  // inside a nested begin does not keep its value across the enclosing
      [*] = ;                  // loop (six army counters were read as zero on 19.09 for exactly this).
      [*] = ;                  var hcfree : Boolean;
      [*] = ;                  for hci := 0 to gc_country_maxfixedproduce-1 do
      [*] = ;                  for hcjj := 0 to gc_country_fixedproduce_maxcount-1 do
      [*] = ;                  if (hcbid < 0) and (SameText(gCountry[hccid].fixedproduce[hci].build[hcjj].id, hcsid2)) then
      [*] = ;                  hcbid := _unit_ConvertObjSIDToID(hccid, gCountry[hccid].fixedproduce[hci].id);
      [*] = ;                  if (hcbid >= 0) then
      [*] = ;                  begin
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hbgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hbpo : Pointer = _unit_GetTObj(hbgo);
      [*] = ;                        if (hbpo<>nil) and (TObj(hbpo).id = hcbid) and (TObj(hbpo).cid = hccid) then
      [*] = ;                        if (TObj(hbpo).bbuilt) then
      [*] = ;                        gIntegerList.Add(hbgo);
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount > 0) then
      [*] = ;                     begin
      [*] = ;                        // The engine ANSWERS whether it took the order, and until
      [*] = ;                        // 17.09 the bridge threw that answer away: it logged the
      [*] = ;                        // order and called it a day. Series base14: 345 of 348
      [*] = ;                        // TRAIN orders were infinite, and a refused one looked
      [*] = ;                        // exactly like a working conveyor.
      [*] = ;                        // IS IT ALREADY ORDERED? Live game 17.09: all sixteen
      [*] = ;                        // refusals in one match were for a unit that already had an
      [*] = ;                        // INFINITE order standing in the same building - food, gold
      [*] = ;                        // and housing were all fine, can_inf was true. The engine
      [*] = ;                        // simply will not take a second infinite order for the same
      [*] = ;                        // unit, and the bridge reported that as a bare refusal. That
      [*] = ;                        // is the whole of the '89 percent of TRAIN orders are
      [*] = ;                        // redundant' finding from series base14.
      [*] = ;                        // Count the buildings that ALREADY carry the infinite order,
      [*] = ;                        // do not just note that ONE of them does. Measured live on
      [*] = ;                        // 17.09: one barracks with a plain order gives +20 fighters in
      [*] = ;                        // 95 game seconds, two give +36 in 84 - the second barracks
      [*] = ;                        // DOUBLES the flow. But the model orders with TRAIN -1, and
      [*] = ;                        // this guard skipped that order as soon as the FIRST barracks
      [*] = ;                        // had it, so the second one stood empty and 2500 gold were
      [*] = ;                        // thrown away. The critic asked for a second barracks in 21
      [*] = ;                        // write-ups out of 62 and was right; our own bridge made his
      [*] = ;                        // advice useless.
      [*] = ;                        var hcalready : Boolean = False;
      [*] = ;                        var hcalreadyn : Integer;
      [*] = ;                        for hck := 0 to gIntegerList.GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hcbo : Pointer = _unit_GetTObj(gIntegerList.Get(hck));
      [*] = ;                           if (hcbo<>nil) then
      [*] = ;                           for hcjj := 0 to gc_obj_MaxOrderCount-1 do
      [*] = ;                           begin
      [*] = ;                              var hcpo : Pointer = TObj(hcbo).orders[hcjj];
      [*] = ;                              if (hcpo<>nil) then
      [*] = ;                              if (TOrder(hcpo).itype = gc_obj_order_type_produce) then
      [*] = ;                              if (TOrder(hcpo).info.produceid = hcid) then
      [*] = ;                              if (TOrder(hcpo).info.amount = gc_obj_order_produce_infinite) then
      [*] = ;                              hcalreadyn := hcalreadyn + 1;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hcalreadyn >= gIntegerList.GetCount) then
      [*] = ;                        hcalready := True;
      [*] = ;                        // 13.10, par.147a: GIVE THE INFINITE ORDER ONLY TO BUILDINGS THAT
      [*] = ;                        // LACK IT. The second barracks hired in neither live match D2 nor
      [*] = ;                        // D4: ba_queues stayed '1:pikeman:inf,2:none' to the end. Python
      [*] = ;                        // does repeat TRAIN infantry17 -1 when some barracks has no queue,
      [*] = ;                        // but this branch handed the order to the WHOLE list, and the
      [*] = ;                        // engine will not take a second infinite order for the same unit in
      [*] = ;                        // a building that already carries one (live game 17.09: all sixteen
      [*] = ;                        // refusals were of that kind). Whether it accepts a mixed list was
      [*] = ;                        // never known - so do not rely on it: rebuild the list from the
      [*] = ;                        // buildings that have no such order. Finite orders (musketeers by
      [*] = ;                        // three) are untouched - they go to any barracks as before.
      [*] = ;                        if (hca2 <= gc_obj_order_produce_infinite) and (hcalreadyn > 0) then
      [*] = ;                        if (hcalreadyn < gIntegerList.GetCount) then
      [*] = ;                        begin
      [*] = ;                           gIntegerList.Clear;
      [*] = ;                           for hck := 0 to hcobjn-1 do
      [*] = ;                           begin
      [*] = ;                              var hngo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                              var hnpo : Pointer = _unit_GetTObj(hngo);
      [*] = ;                              if (hnpo<>nil) and (TObj(hnpo).id = hcbid) and (TObj(hnpo).cid = hccid) then
      [*] = ;                              if (TObj(hnpo).bbuilt) then
      [*] = ;                              begin
      [*] = ;                                 hcfree := True;
      [*] = ;                                 for hcjj := 0 to gc_obj_MaxOrderCount-1 do
      [*] = ;                                 begin
      [*] = ;                                    var hnord : Pointer = TObj(hnpo).orders[hcjj];
      [*] = ;                                    if (hnord<>nil) then
      [*] = ;                                    if (TOrder(hnord).itype = gc_obj_order_type_produce) then
      [*] = ;                                    if (TOrder(hnord).info.produceid = hcid) then
      [*] = ;                                    if (TOrder(hnord).info.amount = gc_obj_order_produce_infinite) then
      [*] = ;                                    hcfree := False;
      [*] = ;                                 end;
      [*] = ;                                 if (hcfree) then
      [*] = ;                                 gIntegerList.Add(hngo);
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        // 13.10, par.147b: TRAIN <unit> 0 CANCELS the infinite order.
      [*] = ;                        // Needed to buy mil.1 (750 food) in time: the peasant conveyor
      [*] = ;                        // takes 100 food every 12 s, and in live match D4 food circled
      [*] = ;                        // 450-650 from 3:24 to 6:42 and never reached 750, so mil.1 came
      [*] = ;                        // at 6:48 instead of the player's 3:00-5:30. The engine does this
      [*] = ;                        // with the SAME call and the sixth argument False -
      [*] = ;                        // lib/scenario.script:2570 (GroupCancelProduceUnit trigger).
      [*] = ;                        // Until now a2 = 0 fell through to ProduceUnit with amount 0,
      [*] = ;                        // whose meaning nobody knew.
      [*] = ;                        if (hca2 = 0) then
      [*] = ;                        begin
      [*] = ;                           var hccan : Boolean = _unit_ProduceUnit(hcph, gIntegerList,
      [*] = ;                                hccid, hcid, gc_obj_order_produce_infinite, False, True, True);
      [*] = ;                           if (hccan) then
      [*] = ;                           Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] +
      [*] = ;                                ' x0 - infinite order cancelled in ' + IntToStr(gIntegerList.GetCount) + ' buildings')
      [*] = ;                           else
      [*] = ;                           Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] +
      [*] = ;                                ' x0 - the game did not cancel the order');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        if (hcalready) and (hca2 <= gc_obj_order_produce_infinite) then
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'TRAIN ' +
      [*] = ;                                gCountry[hccid].members[hcid] + ': ALREADY ORDERED without ' +
      [*] = ;                                'count and still running. The conveyor works, the order is ' +
      [*] = ;                                'not needed - spend the tick on something else');
      [*] = ;                           Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] +
      [*] = ;                                ' - already ordered, skipped');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                        var hctok : Boolean = _unit_ProduceUnit(hcph, gIntegerList,
      [*] = ;                             hccid, hcid, hca2, True, True, True);
      [*] = ;                        if (hctok) then
      [*] = ;                        Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] + ' x' +
      [*] = ;                            IntToStr(hca2) + ' in ' + IntToStr(gIntegerList.GetCount) +
      [*] = ;                            ' buildings (already in ' + IntToStr(hcalreadyn) + ')')
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'TRAIN ' +
      [*] = ;                                gCountry[hccid].members[hcid] + ': THE GAME DID NOT TAKE ' +
      [*] = ;                                'THE ORDER. The building is there, so look at the queue ' +
      [*] = ;                                '(train_now) and at the food');
      [*] = ;                           Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] +
      [*] = ;                                ' - REFUSED by the game');
      [*] = ;                        end;
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'TRAIN ' +
      [*] = ;                          gCountry[hccid].members[hcid] + ': the building that makes it is not built');
      [*] = ;                     Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] + ' - no producer built yet');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'BALANCE') then
      [*] = ;               begin
      [*] = ;                  // a1: 0 food, 1 wood, 2 stone; a2: how many peasants to have on it.
      [*] = ;                  // A human slot has no resbalance table - we give the orders
      [*] = ;                  // ourselves, and only to IDLE peasants: pulling a working one off
      [*] = ;                  // its resource is what the engine does, and what ruined our early
      [*] = ;                  // episodes.
      [*] = ;                  var hbres : Integer = -1;
      [*] = ;                  if (hca1 = 0) then hbres := gc_resource_type_food;
      [*] = ;                  if (hca1 = 1) then hbres := gc_resource_type_wood;
      [*] = ;                  if (hca1 = 2) then hbres := gc_resource_type_stone;
      [*] = ;                  if (hbres >= 0) and (hca2 > 0) then
      [*] = ;                  begin
      [*] = ;                     var hbhave : Integer;
      [*] = ;                     var hbout : Integer = 0;     // how many are too many on this resource
      [*] = ;                     var hblet : Integer = 0;     // how many of them were taken off
      [*] = ;                     var hbcf : Integer = 0;      // 28.10: men now on food / wood / stone (for the donor rule)
      [*] = ;                     var hbcw : Integer = 0;
      [*] = ;                     var hbcs : Integer = 0;
      [*] = ;                     var hbkept : Integer = 0;    // donors refused: their resource is not above its target
      [*] = ;                     gTmpIntList.Clear;
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hbgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hbpo : Pointer = _unit_GetTObj(hbgo);
      [*] = ;                        if (hbpo<>nil) then
      [*] = ;                        if (gObjProp[TObj(hbpo).cid][TObj(hbpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        if (TObj(hbpo).insideofuid = 0) then
      [*] = ;                        begin
      [*] = ;                           var hbot : Integer = TObj(hbpo).orders[0].itype;
      [*] = ;                           if (hbot = gc_obj_order_type_gainres) then
      [*] = ;                           begin
      [*] = ;                              var hbrp : Pointer = _res_GetTRes(TObj(hbpo).orders[0].info.trg);
      [*] = ;                              if (hbrp<>nil) and (TRes(hbrp).itype = hbres) then
      [*] = ;                              hbhave := hbhave + 1;
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           if (hbot = gc_obj_order_type_none) then
      [*] = ;                           gTmpIntList.Add(hbgo);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     // TAKING OFF THE EXTRA ONES (23.10, task No2 of the mac, games D11 and D12).
      [*] = ;                     // Ground BALANCE could only ever ADD. After the academy TWELVE men stood on
      [*] = ;                     // stone until the end of two games in a row while the strategy asked for four:
      [*] = ;                     // the why line said 'stone taken by 12' every tick and nobody moved, and the
      [*] = ;                     // examiner's answer was unanimous - those twelve belong on food. The mine
      [*] = ;                     // branch already lets men out of a mine; this is the same for the ground.
      [*] = ;                     // _unit_ClearOrders is what the game's OWN economic AI calls before moving a
      [*] = ;                     // gatherer (progresseconomicai.inc:583), and the player's order path calls it
      [*] = ;                     // too (readorder.inc:51): the man goes idle, and the next BALANCE - this very
      [*] = ;                     // tick or the following one - takes idle men FIRST.
      [*] = ;                     // 29.10 (mac, No1b): the sink seats every idle man, so a repeated target is often BELOW the count.
      [*] = ;                     // Men come off only when python lowered its target since the last file (hbold = previous target,
      [*] = ;                     // -1 = none yet), and only as many as it released - the rest stay where they work.
      [*] = ;                     var hbold : Integer = hcof;
      [*] = ;                     if (hca1 = 1) then hbold := hcow;
      [*] = ;                     if (hca1 = 2) then hbold := hcos;
      [*] = ;                     if ((hbold < 0) or (hca2 < hbold)) and (hbhave > hca2) then
      [*] = ;                     begin
      [*] = ;                        hbout := hbhave - hca2;
      [*] = ;                        if (hbold >= 0) then
      [*] = ;                        begin
      [*] = ;                           if (hbold - hca2 < hbout) then hbout := hbold - hca2;
      [*] = ;                        end;
      [*] = ;                        for hck := 0 to hcobjn-1 do
      [*] = ;                        if (hblet < hbout) then
      [*] = ;                        begin
      [*] = ;                           var hbgo3 : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hbpo3 : Pointer = _unit_GetTObj(hbgo3);
      [*] = ;                           if (hbpo3<>nil) then
      [*] = ;                           if (gObjProp[TObj(hbpo3).cid][TObj(hbpo3).id].usage = gc_obj_usage_peasant) then
      [*] = ;                           if (TObj(hbpo3).insideofuid = 0) then
      [*] = ;                           if (TObj(hbpo3).orders[0].itype = gc_obj_order_type_gainres) then
      [*] = ;                           begin
      [*] = ;                              var hbrp4 : Pointer = _res_GetTRes(TObj(hbpo3).orders[0].info.trg);
      [*] = ;                              if (hbrp4<>nil) then
      [*] = ;                              if (TRes(hbrp4).itype = hbres) then
      [*] = ;                              begin
      [*] = ;                                 _unit_ClearOrders(hbgo3);
      [*] = ;                                 hblet := hblet + 1;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                             ': ' + IntToStr(hbhave) + ' gathered it, asked for ' + IntToStr(hca2) +
      [*] = ;                             ', took off ' + IntToStr(hblet) + ' - they are idle now');
      [*] = ;                        Log('bridge-human: GATHER res' + IntToStr(hca1) + ' took off ' +
      [*] = ;                            IntToStr(hblet) + ', had ' + IntToStr(hbhave) + ', asked ' + IntToStr(hca2));
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (hbhave > hca2) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                             ': ' + IntToStr(hbhave) + ' gather it, asked for ' + IntToStr(hca2) +
      [*] = ;                             ' - same target as before, the extra men were seated by the sink and stay');
      [*] = ;                        Log('bridge-human: GATHER res' + IntToStr(hca1) + ' kept ' + IntToStr(hbhave - hca2) +
      [*] = ;                            ' over target (no new decrease), had ' + IntToStr(hbhave) + ', asked ' + IntToStr(hca2));
      [*] = ;                     end;
      [*] = ;                     // Second pass: if idle peasants are not enough, take them off ANOTHER
      [*] = ;                     // resource. Without this BALANCE could only ever place idle men, and in the
      [*] = ;                     // live game of 12.09 the model watched food stay at 3 people while it asked
      [*] = ;                     // for 12 nine ticks in a row - everyone was already busy on wood and stone.
      [*] = ;                     // The engine strips gatherers for construction, so this is the game s own
      [*] = ;                     // behaviour rather than an invention of ours.
      [*] = ;                     // 28.10 (mac, after D18): a donor is taken only from a resource that stands ABOVE its
      [*] = ;                     // own target in this file (hcbtf/hcbtw/hcbts; -1 = no target, any man may go). Counted
      [*] = ;                     // HERE, after the take-offs above made their men idle, and decremented per donor.
      [*] = ;                     if (hbhave + gTmpIntList.GetCount < hca2) then
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hbgo4 : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hbpo4 : Pointer = _unit_GetTObj(hbgo4);
      [*] = ;                        if (hbpo4<>nil) then
      [*] = ;                        if (gObjProp[TObj(hbpo4).cid][TObj(hbpo4).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        if (TObj(hbpo4).insideofuid = 0) then
      [*] = ;                        if (TObj(hbpo4).orders[0].itype = gc_obj_order_type_gainres) then
      [*] = ;                        begin
      [*] = ;                           var hbrp5 : Pointer = _res_GetTRes(TObj(hbpo4).orders[0].info.trg);
      [*] = ;                           if (hbrp5<>nil) then
      [*] = ;                           begin
      [*] = ;                              if (TRes(hbrp5).itype = gc_resource_type_food) then hbcf := hbcf + 1;
      [*] = ;                              if (TRes(hbrp5).itype = gc_resource_type_wood) then hbcw := hbcw + 1;
      [*] = ;                              if (TRes(hbrp5).itype = gc_resource_type_stone) then hbcs := hbcs + 1;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (hbhave + gTmpIntList.GetCount < hca2) then
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                        if (hbhave + gTmpIntList.GetCount < hca2) then
      [*] = ;                        begin
      [*] = ;                           var hbgo2 : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hbpo2 : Pointer = _unit_GetTObj(hbgo2);
      [*] = ;                           if (hbpo2<>nil) then
      [*] = ;                           if (gObjProp[TObj(hbpo2).cid][TObj(hbpo2).id].usage = gc_obj_usage_peasant) then
      [*] = ;                           if (TObj(hbpo2).insideofuid = 0) then
      [*] = ;                           if (TObj(hbpo2).orders[0].itype = gc_obj_order_type_gainres) then
      [*] = ;                           begin
      [*] = ;                              var hbrp3 : Pointer = _res_GetTRes(TObj(hbpo2).orders[0].info.trg);
      [*] = ;                              if (hbrp3<>nil) and (TRes(hbrp3).itype <> hbres) then
      [*] = ;                              begin
      [*] = ;                                 var hbdt : Integer = TRes(hbrp3).itype;
      [*] = ;                                 var hbdok : Boolean = True;
      [*] = ;                                 if (hbdt = gc_resource_type_food) and (hcbtf >= 0) then
      [*] = ;                                 begin
      [*] = ;                                    if (hbcf <= hcbtf) then hbdok := False;
      [*] = ;                                 end;
      [*] = ;                                 if (hbdt = gc_resource_type_wood) and (hcbtw >= 0) then
      [*] = ;                                 begin
      [*] = ;                                    if (hbcw <= hcbtw) then hbdok := False;
      [*] = ;                                 end;
      [*] = ;                                 if (hbdt = gc_resource_type_stone) and (hcbts >= 0) then
      [*] = ;                                 begin
      [*] = ;                                    if (hbcs <= hcbts) then hbdok := False;
      [*] = ;                                 end;
      [*] = ;                                 if (hbdok) then
      [*] = ;                                 begin
      [*] = ;                                    gTmpIntList.Add(hbgo2);
      [*] = ;                                    if (hbdt = gc_resource_type_food) then hbcf := hbcf - 1;
      [*] = ;                                    if (hbdt = gc_resource_type_wood) then hbcw := hbcw - 1;
      [*] = ;                                    if (hbdt = gc_resource_type_stone) then hbcs := hbcs - 1;
      [*] = ;                                 end
      [*] = ;                                 else
      [*] = ;                                 begin
      [*] = ;                                    hbkept := hbkept + 1;
      [*] = ;                                 end;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     if (hbkept > 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                             ': ' + IntToStr(hbkept) + ' men kept on resources at or below their own target in this file');
      [*] = ;                        Log('bridge-human: GATHER res' + IntToStr(hca1) + ' kept ' + IntToStr(hbkept) + ' donors (their resource not above its target)');
      [*] = ;                     end;
      [*] = ;                     if (hbhave < hca2) and (gTmpIntList.GetCount > 0) then
      [*] = ;                     begin
      [*] = ;                        // Nearest raised deposit of this type around the base.
      [*] = ;                        gIntegerList.Clear;
      [*] = ;                        // Flags are (bcheckdist, bincludefood, bincludewood, bincludestone,
      [*] = ;                        // bincludemines). Only food was on: for a whole live game BALANCE wood
      [*] = ;                        // and stone could not find a deposit at all, and the model spent eight
      [*] = ;                        // ticks writing that the order goes out but nobody starts gathering.
      [*] = ;                        // The itype filter below picks the right kind, so include all three.
      [*] = ;                        // FOOD IS SEARCHED AROUND THE MILL, not around the town
      [*] = ;                        // hall. That is what the game itself does:
      [*] = ;                        // _ai_SendFreePeasantsToGainFood takes the mill from
      [*] = ;                        // milllist, reads ITS position and calls the same search
      [*] = ;                        // with radius 30 (progresseconomicai.inc:709+). Ours looked
      [*] = ;                        // 40 around the hall, and when the mill stood further out the
      [*] = ;                        // field simply was not in the list: the bridge answered 'no
      [*] = ;                        // deposit of this kind within 40 of the base' and nobody ever
      [*] = ;                        // went to food. Measured 17.09 on 15 games of base15: in the
      [*] = ;                        // window 1:00-3:30 the model gave BALANCE food 94 times in 100
      [*] = ;                        // ticks and on_food stayed at ZERO in 68 of them, with the mill
      [*] = ;                        // already built in 67. The refusal was printed 29 times.
      [*] = ;                        var hbfx : Float = hcx;
      [*] = ;                        var hbfz : Float = hcz;
      [*] = ;                        if (hbres = gc_resource_type_food) then
      [*] = ;                        begin
      [*] = ;                           var hbmk : Integer;
      [*] = ;                           var hbmill : Integer = 0;
      [*] = ;                           for hbmk := 0 to hcobjn-1 do
      [*] = ;                           begin
      [*] = ;                              var hbmgo : Integer = GetGameObjectHandleByIndex(hbmk, hcph);
      [*] = ;                              var hbmpo : Pointer = _unit_GetTObj(hbmgo);
      [*] = ;                              if (hbmpo<>nil) and (hbmill = 0) then
      [*] = ;                              if (gObjProp[TObj(hbmpo).cid][TObj(hbmpo).id].airole = gc_ai_unit_mill) then
      [*] = ;                              if (TObj(hbmpo).bbuilt) then
      [*] = ;                              begin
      [*] = ;                                 hbmill := hbmgo;
      [*] = ;                                 hbfx := GetGameObjectPositionXByHandle(hbmgo);
      [*] = ;                                 hbfz := GetGameObjectPositionZByHandle(hbmgo);
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        _misc_MakeListEnvironmentInRadius(hbfx, hbfz, 40, True, True, True, True, False, gIntegerList);
      [*] = ;                        var hbtrg : Integer = 0;
      [*] = ;                        var hbbest : Float = 1000000;
      [*] = ;                        for hck := 0 to gIntegerList.GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hbh : Integer = gIntegerList.Get(hck);
      [*] = ;                           var hbrp2 : Pointer = _res_GetTRes(hbh);
      [*] = ;                           if (hbrp2<>nil) then
      [*] = ;                           if (TRes(hbrp2).brised) and (TRes(hbrp2).itype = hbres) then
      [*] = ;                           begin
      [*] = ;                              var hbd : Float = VectorDistance(GetGameObjectPositionXByHandle(hbh), 0,
      [*] = ;                                   GetGameObjectPositionZByHandle(hbh), hcx, 0, hcz);
      [*] = ;                              if (hbd < hbbest) then
      [*] = ;                              begin
      [*] = ;                                 hbbest := hbd;
      [*] = ;                                 hbtrg := hbh;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hbtrg <> 0) then
      [*] = ;                        begin
      [*] = ;                           var hbneed : Integer = hca2 - hbhave;
      [*] = ;                           while (gTmpIntList.GetCount > hbneed) do
      [*] = ;                           gTmpIntList.Delete(gTmpIntList.GetCount-1);
      [*] = ;                           // _order_OrderUnitsToGainResource is declared INSIDE
      [*] = ;                           // progresseconomicai.inc - local to the EconomicAI state, invisible
      [*] = ;                           // from Progress. Calling it does not compile and kills the whole tick.
      [*] = ;                           // Found by bisection 12.09. lib/unit.script gives a per-unit order.
      [*] = ;                           var hbpx : Float = GetGameObjectPositionXByHandle(hbtrg);
      [*] = ;                           var hbpz : Float = GetGameObjectPositionZByHandle(hbtrg);
      [*] = ;                           for hck := 0 to gTmpIntList.GetCount-1 do
      [*] = ;                           _unit_OrderGainResource(gTmpIntList.Get(hck), hbtrg, hbpx, hbpz);
      [*] = ;                           Log('bridge-human: GATHER res' + IntToStr(hca1) + ' sent ' +
      [*] = ;                               IntToStr(gTmpIntList.GetCount) + ' peasants, had ' + IntToStr(hbhave));
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'GATHER res' + IntToStr(hca1) +
      [*] = ;                             ': no deposit of this kind within 40. Food is searched around the ' +
      [*] = ;                             'MILL, wood and stone around the town hall. Sow a field (SEED) or ' +
      [*] = ;                             'build closer to the deposit');
      [*] = ;                        Log('bridge-human: GATHER res' + IntToStr(hca1) + ' - no deposit within 40 of base');
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'BALANCE') and (hca1 >= 3) and (hca1 <= 5) and (hca2 > 0) then
      [*] = ;               begin
      [*] = ;                  // Mines: gold, iron, coal. A peasant works a mine from INSIDE, so this is
      [*] = ;                  // not a gather order but a go-inside order.
      [*] = ;                  //
      [*] = ;                  // 15.09: this branch had two blind spots, both found by counting traces.
      [*] = ;                  // 'Already inside' counted peasants inside ANY building, so three men in the
      [*] = ;                  // iron mine turned 'BALANCE gold 3' into a silent no-op. And only the FIRST
      [*] = ;                  // mine of the kind was ever filled - a second gold mine stayed empty forever.
      [*] = ;                  // Now both the counting and the filling go mine by mine, the way the engine
      [*] = ;                  // fills them itself in _ai_FillMines (progresseconomicai.inc:1305).
      [*] = ;                  var hmrole : Integer = gc_ai_unit_minegold;
      [*] = ;                  if (hca1 = 4) then hmrole := gc_ai_unit_mineiron;
      [*] = ;                  if (hca1 = 5) then hmrole := gc_ai_unit_minecoal;
      [*] = ;                  var hmk, hmk2 : Integer;
      [*] = ;                  var hmine : Integer = 0;
      [*] = ;                  var hminside : Integer = 0;
      [*] = ;                  var hmfree : Integer = 0;
      [*] = ;                  // 17.09: a scalar declared inside a nested begin does not accumulate,
      [*] = ;                  // so the let-out counters live here, where hminside lives.
      [*] = ;                  var hmout : Integer = 0;
      [*] = ;                  var hmlet : Integer = 0;
      [*] = ;                  // 29.10 (mac, No1b): the sink leaves no idle men, so a mine is filled from the ground too -
      [*] = ;                  // only from a resource ABOVE its stored target (hcstf/hcstw/hcsts; -1 = no target, any man may go),
      [*] = ;                  // i.e. from the very men who would have stood idle before. Counters live here (scalar lesson).
      [*] = ;                  var hmcf : Integer = 0;
      [*] = ;                  var hmcw : Integer = 0;
      [*] = ;                  var hmcs : Integer = 0;
      [*] = ;                  var hmdon : Integer = 0;
      [*] = ;                  // First pass: mines of this kind built, men already inside THEM, and men
      [*] = ;                  // free to be sent at all.
      [*] = ;                  for hmk := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hmgo : Integer = GetGameObjectHandleByIndex(hmk, hcph);
      [*] = ;                     var hmpo : Pointer = _unit_GetTObj(hmgo);
      [*] = ;                     if (hmpo<>nil) then
      [*] = ;                     begin
      [*] = ;                        if (gObjProp[TObj(hmpo).cid][TObj(hmpo).id].airole = hmrole) then
      [*] = ;                        if (TObj(hmpo).bbuilt) then
      [*] = ;                        hmine := hmine + 1;
      [*] = ;                        if (gObjProp[TObj(hmpo).cid][TObj(hmpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        begin
      [*] = ;                           if (TObj(hmpo).insideofuid <> 0) then
      [*] = ;                           begin
      [*] = ;                              var hmih : Integer = GetGameObjectHandleByUniqueId(TObj(hmpo).insideofuid);
      [*] = ;                              var hmip : Pointer = _unit_GetTObj(hmih);
      [*] = ;                              if (hmip<>nil) then
      [*] = ;                              if (gObjProp[TObj(hmip).cid][TObj(hmip).id].airole = hmrole) then
      [*] = ;                              hminside := hminside + 1;
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           if (TObj(hmpo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                           begin
      [*] = ;                              hmfree := hmfree + 1;
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           if (TObj(hmpo).orders[0].itype = gc_obj_order_type_gainres) then
      [*] = ;                           begin
      [*] = ;                              var hmrp : Pointer = _res_GetTRes(TObj(hmpo).orders[0].info.trg);
      [*] = ;                              if (hmrp<>nil) then
      [*] = ;                              begin
      [*] = ;                                 if (TRes(hmrp).itype = gc_resource_type_food) then hmcf := hmcf + 1;
      [*] = ;                                 if (TRes(hmrp).itype = gc_resource_type_wood) then hmcw := hmcw + 1;
      [*] = ;                                 if (TRes(hmrp).itype = gc_resource_type_stone) then hmcs := hmcs + 1;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hcstf < 0) then hmdon := hmdon + hmcf;
      [*] = ;                  if (hcstw < 0) then hmdon := hmdon + hmcw;
      [*] = ;                  if (hcsts < 0) then hmdon := hmdon + hmcs;
      [*] = ;                  if (hcstf >= 0) then
      [*] = ;                  begin
      [*] = ;                     if (hmcf > hcstf) then hmdon := hmdon + hmcf - hcstf;
      [*] = ;                  end;
      [*] = ;                  if (hcstw >= 0) then
      [*] = ;                  begin
      [*] = ;                     if (hmcw > hcstw) then hmdon := hmdon + hmcw - hcstw;
      [*] = ;                  end;
      [*] = ;                  if (hcsts >= 0) then
      [*] = ;                  begin
      [*] = ;                     if (hmcs > hcsts) then hmdon := hmdon + hmcs - hcsts;
      [*] = ;                  end;
      [*] = ;                  // Silence is indistinguishable from doing nothing: every refusal says why,
      [*] = ;                  // and the reason goes back into the next request.
      [*] = ;                  if (hmine = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': no such mine is built yet');
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - no mine built');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hminside > hca2) then
      [*] = ;                  begin
      [*] = ;                     // 20.10, game D9: this branch only ever ADDED men. The strategy asked
      [*] = ;                     // BALANCE gold 5 from 7:00 on while fifteen worked the mine, and the only
      [*] = ;                     // answer was '15 already work that mine' - 44 times in one game. So the
      [*] = ;                     // gold cap (153) and gold-off-for-a-need (166b) never moved a single man
      [*] = ;                     // in a live game: taking away was a line in why and nothing else. Now the
      [*] = ;                     // extra men are let out, mine by mine, the way the native AI empties a
      [*] = ;                     // transport (progresswarai.inc:3899) and the player does by the leave
      [*] = ;                     // button (ReadLeaveOrder) - the same call, _unit_DoUnitsGoOutside.
      [*] = ;                     hmout := hminside - hca2;
      [*] = ;                     for hmk := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hmoo : Integer = GetGameObjectHandleByIndex(hmk, hcph);
      [*] = ;                        var hmop : Pointer = _unit_GetTObj(hmoo);
      [*] = ;                        if (hmop<>nil) then
      [*] = ;                        if (gObjProp[TObj(hmop).cid][TObj(hmop).id].airole = hmrole) then
      [*] = ;                        if (TObj(hmop).bbuilt) then
      [*] = ;                        if (hmlet < hmout) then
      [*] = ;                        begin
      [*] = ;                           // The men inside are a TIntegerList of handles owned by the building;
      [*] = ;                           // _unit_OrderExitUnit reorders that list, so copy the handles out
      [*] = ;                           // first and only then order them out (lib/unit.script:4543).
      [*] = ;                           var hmil : Pointer = _misc_GetObjectArgData(hmoo, gc_argunit_inside);
      [*] = ;                           if (hmil<>nil) then
      [*] = ;                           begin
      [*] = ;                              var hmwas : Integer = TIntegerList(hmil).GetCount;
      [*] = ;                              gIntegerList.Clear;
      [*] = ;                              for hmk2 := 0 to hmwas-1 do
      [*] = ;                              if (hmlet + gIntegerList.GetCount < hmout) then
      [*] = ;                              gIntegerList.Add(TIntegerList(hmil).Get(hmk2));
      [*] = ;                              if (gIntegerList.GetCount > 0) then
      [*] = ;                              begin
      [*] = ;                                 Log('bridge-human: MINE res' + IntToStr(hca1) + ' let out ' +
      [*] = ;                                     IntToStr(gIntegerList.GetCount) + ', inside was ' + IntToStr(hmwas));
      [*] = ;                                 hmlet := hmlet + gIntegerList.GetCount;
      [*] = ;                                 _unit_DoUnitsGoOutside(gIntegerList, False, True);
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': ' + IntToStr(hminside) + ' worked that mine, asked for ' + IntToStr(hca2) + ', let out ' + IntToStr(hmlet));
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hminside = hca2) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': ' + IntToStr(hminside) + ' already work that mine, asked for ' + IntToStr(hca2));
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - already inside ' + IntToStr(hminside));
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hmfree + hmdon = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': no idle peasant to send, and every resource stands at or below its target - lower one first');
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - no idle peasants and no resource above its target');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hmsent : Integer = 0;
      [*] = ;                     var hmroom : Integer = 0;
      [*] = ;                     // Second pass: fill mine by mine, each up to its OWN free places. The
      [*] = ;                     // formula is the engine's: places minus those inside minus those already
      [*] = ;                     // on their way (insidereserved).
      [*] = ;                     for hmk := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hmbo : Integer = GetGameObjectHandleByIndex(hmk, hcph);
      [*] = ;                        var hmbp : Pointer = _unit_GetTObj(hmbo);
      [*] = ;                        if (hmbp<>nil) then
      [*] = ;                        if (gObjProp[TObj(hmbp).cid][TObj(hmbp).id].airole = hmrole) then
      [*] = ;                        if (TObj(hmbp).bbuilt) then
      [*] = ;                        if (hminside + hmsent < hca2) then
      [*] = ;                        begin
      [*] = ;                           var hmuid : Integer = GetGameObjectUniqueIdByHandle(hmbo);
      [*] = ;                           var hmthis : Integer = 0;
      [*] = ;                           for hmk2 := 0 to hcobjn-1 do
      [*] = ;                           begin
      [*] = ;                              var hmgo2 : Integer = GetGameObjectHandleByIndex(hmk2, hcph);
      [*] = ;                              var hmpo2 : Pointer = _unit_GetTObj(hmgo2);
      [*] = ;                              if (hmpo2<>nil) then
      [*] = ;                              if (gObjProp[TObj(hmpo2).cid][TObj(hmpo2).id].usage = gc_obj_usage_peasant) then
      [*] = ;                              if (TObj(hmpo2).insideofuid = hmuid) then
      [*] = ;                              hmthis := hmthis + 1;
      [*] = ;                           end;
      [*] = ;                           hmroom := gObjProp[TObj(hmbp).cid][TObj(hmbp).id].peasantabsorber +
      [*] = ;                                TObj(hmbp).individual.addpeasantabsorber - hmthis - TObj(hmbp).insidereserved;
      [*] = ;                           var hmneed : Integer = hca2 - hminside - hmsent;
      [*] = ;                           if (hmroom > hmneed) then
      [*] = ;                           hmroom := hmneed;
      [*] = ;                           if (hmroom > 0) then
      [*] = ;                           begin
      [*] = ;                              gTmpIntList.Clear;
      [*] = ;                              for hmk2 := 0 to hcobjn-1 do
      [*] = ;                              if (gTmpIntList.GetCount < hmroom) then
      [*] = ;                              begin
      [*] = ;                                 var hmgo3 : Integer = GetGameObjectHandleByIndex(hmk2, hcph);
      [*] = ;                                 var hmpo3 : Pointer = _unit_GetTObj(hmgo3);
      [*] = ;                                 if (hmpo3<>nil) then
      [*] = ;                                 if (gObjProp[TObj(hmpo3).cid][TObj(hmpo3).id].usage = gc_obj_usage_peasant) then
      [*] = ;                                 if (TObj(hmpo3).insideofuid = 0) then
      [*] = ;                                 if (TObj(hmpo3).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                                 gTmpIntList.Add(hmgo3);
      [*] = ;                              end;
      [*] = ;                              // Second pass (No1b): donors off the ground, a resource above its stored target only.
      [*] = ;                              if (gTmpIntList.GetCount < hmroom) then
      [*] = ;                              for hmk2 := 0 to hcobjn-1 do
      [*] = ;                              if (gTmpIntList.GetCount < hmroom) then
      [*] = ;                              begin
      [*] = ;                                 var hmgo4 : Integer = GetGameObjectHandleByIndex(hmk2, hcph);
      [*] = ;                                 var hmpo4 : Pointer = _unit_GetTObj(hmgo4);
      [*] = ;                                 if (hmpo4<>nil) then
      [*] = ;                                 if (gObjProp[TObj(hmpo4).cid][TObj(hmpo4).id].usage = gc_obj_usage_peasant) then
      [*] = ;                                 if (TObj(hmpo4).insideofuid = 0) then
      [*] = ;                                 if (TObj(hmpo4).orders[0].itype = gc_obj_order_type_gainres) then
      [*] = ;                                 begin
      [*] = ;                                    var hmrp4 : Pointer = _res_GetTRes(TObj(hmpo4).orders[0].info.trg);
      [*] = ;                                    if (hmrp4<>nil) then
      [*] = ;                                    begin
      [*] = ;                                       var hmdt : Integer = TRes(hmrp4).itype;
      [*] = ;                                       var hmdok : Boolean = False;
      [*] = ;                                       if (hmdt = gc_resource_type_food) then
      [*] = ;                                       begin
      [*] = ;                                          if (hcstf < 0) then hmdok := True;
      [*] = ;                                          if (hmcf > hcstf) then hmdok := True;
      [*] = ;                                       end;
      [*] = ;                                       if (hmdt = gc_resource_type_wood) then
      [*] = ;                                       begin
      [*] = ;                                          if (hcstw < 0) then hmdok := True;
      [*] = ;                                          if (hmcw > hcstw) then hmdok := True;
      [*] = ;                                       end;
      [*] = ;                                       if (hmdt = gc_resource_type_stone) then
      [*] = ;                                       begin
      [*] = ;                                          if (hcsts < 0) then hmdok := True;
      [*] = ;                                          if (hmcs > hcsts) then hmdok := True;
      [*] = ;                                       end;
      [*] = ;                                       if (hmdok) then
      [*] = ;                                       begin
      [*] = ;                                          gTmpIntList.Add(hmgo4);
      [*] = ;                                          if (hmdt = gc_resource_type_food) then hmcf := hmcf - 1;
      [*] = ;                                          if (hmdt = gc_resource_type_wood) then hmcw := hmcw - 1;
      [*] = ;                                          if (hmdt = gc_resource_type_stone) then hmcs := hmcs - 1;
      [*] = ;                                       end;
      [*] = ;                                    end;
      [*] = ;                                 end;
      [*] = ;                              end;
      [*] = ;                              if (gTmpIntList.GetCount > 0) then
      [*] = ;                              begin
      [*] = ;                                 gPtrList.Clear;
      [*] = ;                                 _player_OrderUnitsToGoInside(plind, gTmpIntList, gPtrList, hmbo, True, False);
      [*] = ;                                 hmsent := hmsent + gTmpIntList.GetCount;
      [*] = ;                                 Log('bridge-human: MINE res' + IntToStr(hca1) + ' sent ' +
      [*] = ;                                     IntToStr(gTmpIntList.GetCount) + ' into one mine, had inside ' +
      [*] = ;                                     IntToStr(hmthis));
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (hmsent = 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                             ': every mine of that kind is full, build one more');
      [*] = ;                        Log('bridge-human: MINE res' + IntToStr(hca1) + ' - all mines full');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               // SEED: order one more field at every mill.
      [*] = ;               //
      [*] = ;               // A field is a UNIT the mill produces (usage = gc_obj_usage_field), not a
      [*] = ;               // button that costs nothing: it is priced at 5 gold (unit.script:1692), and
      [*] = ;               // the engine turns the order into an actual field in doprogressorders.inc:130
      [*] = ;               // by calling _unit_DoSeedWheat. So we place the same ORDER a player places -
      [*] = ;               // calling DoSeedWheat directly would skip both the queue and the price.
      [*] = ;               //
      [*] = ;               // The FIRST field is sown by the game itself when the mill is finished
      [*] = ;               // (ontagstates.inc:140). What nobody did on the human slot is sow AGAIN once
      [*] = ;               // that field is reaped - and that is where the hunger came from: food only
      [*] = ;               // fell, and below 500 the whole endless production stops.
      [*] = ;               // DEFEND a1 (30.10): the switch of the home defence reflex (hcmd tail): 1 on, 0 off; remembered in br_hdef for the rest
      [*] = ;               // of the game. Lets a container copy run with the reflex off against the same strategy file - one difference from the base.
      [*] = ;               if (hccmd = 'DEFEND') then
      [*] = ;               begin
      [*] = ;                  var hcdf : Integer = ParserSelectByKey('br_hdef');
      [*] = ;                  if (hcdf = 0) then
      [*] = ;                  hcdf := ParserCreate('br_hdef');
      [*] = ;                  ParserSetIntValueByKeyByHandle(hcdf, 'defend' + IntToStr(plind), hca1);
      [*] = ;                  // a2 (30.10 evening, list item 2): switch of the DEFENSIVE ATTACK rule (ATTACK branch, hadefn): 1 on, 0 off,
      [*] = ;                  // -1 leaves it as it is; default 1 when never set.
      [*] = ;                  if (hca2 >= 0) then
      [*] = ;                  ParserSetIntValueByKeyByHandle(hcdf, 'atkdef' + IntToStr(plind), hca2);
      [*] = ;                  Log('bridge-human: DEFEND ' + IntToStr(hca1) + ' (home defence reflex switch), attack-defence ' + IntToStr(hca2));
      [*] = ;               end;
      [*] = ;               if (hccmd = 'SEED') then
      [*] = ;               begin
      [*] = ;                  // sid must be a VARIABLE: _unit_ConvertObjSIDToID takes it as
      [*] = ;                  // 'var sid : String' (unit.script:438), a literal does not compile.
      [*] = ;                  // On 13.09 that killed the whole Progress tick - with it the economy
      [*] = ;                  // of BOTH players: nothing was being built anywhere.
      [*] = ;                  var hcfsid : String = 'field';
      [*] = ;                  var hcfid : Integer = _unit_ConvertObjSIDToID(hccid, hcfsid);
      [*] = ;                  gTmpIntList.Clear;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hcmh : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hcmp : Pointer = _unit_GetTObj(hcmh);
      [*] = ;                     if (hcmp<>nil) then
      [*] = ;                     if (gObjProp[TObj(hcmp).cid][TObj(hcmp).id].airole = gc_ai_unit_mill) then
      [*] = ;                     if (TObj(hcmp).bbuilt) then
      [*] = ;                     gTmpIntList.Add(hcmh);
      [*] = ;                  end;
      [*] = ;                  if (gTmpIntList.GetCount = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' +
      [*] = ;                          'SEED: no mill is built yet - fields are sown at a mill');
      [*] = ;                     Log('bridge-human: SEED - no mill built');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hcfid <= 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'SEED: this nation has no field object');
      [*] = ;                     Log('bridge-human: SEED - no field object for this nation');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     // HOW MANY fields at once. Until 21.09 it was hard-wired to one,
      [*] = ;                     // and a reaped quarter could only be re-sown field by field, one
      [*] = ;                     // per tick - twenty game seconds each. The player sows several in
      [*] = ;                     // a row with the mouse, and so should we. a1 carries the count;
      [*] = ;                     // zero or absent means one, as before.
      [*] = ;                     var hcfn : Integer = hca1;
      [*] = ;                     if (hcfn < 1) then
      [*] = ;                     hcfn := 1;
      [*] = ;                     if (hcfn > 20) then
      [*] = ;                     hcfn := 20;
      [*] = ;                     _unit_ProduceUnit(hcph, gTmpIntList, hccid, hcfid, hcfn, True, True, True);
      [*] = ;                     Log('bridge-human: SEED ordered ' + IntToStr(hcfn) + ' at ' + IntToStr(gTmpIntList.GetCount) + ' mills');
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'FORMATION') then
      [*] = ;               begin
      [*] = ;                  // LIST ITEM 3 (1.11): a1=1 - the squad inherits the stand of the men it is built from (31.10: FORMATION took 100
      [*] = ;                  // holding men, my_held 100 -> 0, squad_hold 0 until the next FACE). Counted at creation time, set the same
      [*] = ;                  // way the FACE hold path sets it on squads (TSquad.fStandGround). a1 missing or 0 - as before.
      [*] = ;                  var hfheld : Integer = 0;
      [*] = ;                  // A formation is the last term of the readiness the player
      [*] = ;                  // named, and the only one the bridge could not touch at all.
      [*] = ;                  // The engine gives the bonus ONLY to an officer squad: both an
      [*] = ;                  // officer and a drummer are required (_ai_CreateOfficerSquad,
      [*] = ;                  // progresswarai.inc:3597), and the 'NB' shapes in formations.cfg
      [*] = ;                  // carry zeroes. The set of shapes belongs to the officer type,
      [*] = ;                  // so we ask the country table, exactly as the native AI does,
      [*] = ;                  // and take the most compact one by width+height.
      [*] = ;                  hfoff := 0;
      [*] = ;                  hfdrum := 0;
      [*] = ;                  hfr21 := 0;
      [*] = ;                  hfr22 := 0;
      [*] = ;                  hfr50 := 0;
      [*] = ;                  hfr51 := 0;
      [*] = ;                  hfdead := 0;
      [*] = ;                  gIntegerList.Clear;
      [*] = ;                  gTmpIntList.Clear;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hfgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hfp : Pointer = _unit_GetTObj(hfgo);
      [*] = ;                     // NO CORPSES IN THE SQUAD (29.10 night, mac, after D22/D23 and two container freezes). A dead man stays
      [*] = ;                     // in the player's object list until the engine removes the body, and this selection took him: squads
      [*] = ;                     // built after losses were born with 8 / 5 / 16 dead inside (squad_units above my_insquad from the first
      [*] = ;                     // tick), and every squad order then wrote 'WriteMove checkcount' and 'bdead unit' into the log. Both
      [*] = ;                     // passes skip the dead now - the officer and the drummer too.
      [*] = ;                     if (hfp<>nil) then
      [*] = ;                     if (TObj(hfp).bdead) then
      [*] = ;                     hfdead := hfdead + 1;
      [*] = ;                     if (hfp<>nil) then
      [*] = ;                     if (not TObj(hfp).bdead) then
      [*] = ;                     begin
      [*] = ;                        var hfrole : Integer = gObjProp[TObj(hfp).cid][TObj(hfp).id].airole;
      [*] = ;                        var hfu : Integer = gObjProp[TObj(hfp).cid][TObj(hfp).id].usage;
      [*] = ;                        if (hfrole = gc_ai_unit_officer17) then
      [*] = ;                        hfr21 := hfr21 + 1;
      [*] = ;                        if (hfrole = gc_ai_unit_drummer17) then
      [*] = ;                        hfr22 := hfr22 + 1;
      [*] = ;                        if (hfrole = gc_ai_unit_officer18) then
      [*] = ;                        hfr50 := hfr50 + 1;
      [*] = ;                        if (hfrole = gc_ai_unit_drummer18) then
      [*] = ;                        hfr51 := hfr51 + 1;
      [*] = ;                        if (hfoff = 0) and ((hfrole = gc_ai_unit_officer17) or (hfrole = gc_ai_unit_officer18)) then
      [*] = ;                        hfoff := hfgo;
      [*] = ;                        if (hfdrum = 0) and ((hfrole = gc_ai_unit_drummer17) or (hfrole = gc_ai_unit_drummer18)) then
      [*] = ;                        hfdrum := hfgo;
      [*] = ;                        if (hfu = gc_obj_usage_lightinfantry) or (hfu = gc_obj_usage_weak) or
      [*] = ;                           (hfu = gc_obj_usage_grenadier) or (hfu = gc_obj_usage_shooter) or
      [*] = ;                           (hfu = gc_obj_usage_archer) then
      [*] = ;                        gTmpIntList.Add(hfgo);
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hfoff = 0) or (hfdrum = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'FORMATION: a bonus ' +
      [*] = ;                          'formation needs BOTH an officer and a drummer. Have ' +
      [*] = ;                          'officers: ' + IntToStr(hfoff) + ', drummers: ' + IntToStr(hfdrum) +
      [*] = ;                          ' (0 means none free). Train officer17 and drummer17 first');
      [*] = ;                     Log('bridge-human: FORMATION - no officer or no drummer (scanned ' + IntToStr(hcobjn) + ' objects, role 21/22/50/51 seen ' + IntToStr(hfr21) + '/' + IntToStr(hfr22) + '/' + IntToStr(hfr50) + '/' + IntToStr(hfr51) + ', dead skipped ' + IntToStr(hfdead) + ')');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hfsid : String = GetGameObjectBaseNameByHandle(hfoff);
      [*] = ;                     var hfoi : Integer = _country_GetOfficersIndexByOfficerSID(hccid, hfsid);
      [*] = ;                     // WHO may stand in the squad is not a usage class but a
      [*] = ;                     // NAMED LIST of the officer: country.script:2523 gives
      [*] = ;                     // 'officer' the set pikeman, musketeer, musketeernet and
      [*] = ;                     // more, and the native AI reads exactly it
      [*] = ;                     // (progresswarai.inc:3637). The usage filter above kept
      [*] = ;                     // shooters and light infantry only, so a pikeman army -
      [*] = ;                     // ours in every game - built no squad at all. Second pass
      [*] = ;                     // over objects: cheaper than wrong numbers.
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     if (hfoi >= 0) then
      [*] = ;                     begin
      [*] = ;                        for hck := 0 to hcobjn-1 do
      [*] = ;                        begin
      [*] = ;                           var hfg2 : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hfp2 : Pointer = _unit_GetTObj(hfg2);
      [*] = ;                           if (hfp2 <> nil) then
      [*] = ;                           if (not TObj(hfp2).bdead) then
      [*] = ;                           begin
      [*] = ;                              var hfs2 : String = gCountry[hccid].members[TObj(hfp2).id];
      [*] = ;                              for hcj := 0 to gc_country_maxformationunitcount-1 do
      [*] = ;                              begin
      [*] = ;                                 if (hfs2 <> '') and (hfs2 = gCountry[hccid].officers[hfoi].units[hcj]) then
      [*] = ;                                 gIntegerList.Add(hfg2);
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount = 0) then
      [*] = ;                     begin
      [*] = ;                        for hck := 0 to gTmpIntList.GetCount-1 do
      [*] = ;                        gIntegerList.Add(gTmpIntList.Get(hck));
      [*] = ;                     end;
      [*] = ;                     var hfform : Integer = -1;
      [*] = ;                     var hfbest : Integer = -1;
      [*] = ;                     var hfneed : Integer = 1000000;
      [*] = ;                     var hfmen : Integer = gIntegerList.GetCount;
      [*] = ;                     // Choose a USEFUL shape that FITS, not the most compact one.
      [*] = ;                     // Live game 16.09: 'most compact' picked the degenerate
      [*] = ;                     // 'none' formation - squad built, bonuses all zero. A shape
      [*] = ;                     // with no bonus at all (the 'NB' family and 'none') is worth
      [*] = ;                     // nothing, and a shape needing more men than we brought
      [*] = ;                     // cannot form. So: skip the zero ones, keep those that fit,
      [*] = ;                     // and among them take the one asking for the MOST men - the
      [*] = ;                     // wider line is the stronger one.
      [*] = ;                     if (hfoi >= 0) then
      [*] = ;                     for hcj := 0 to gc_country_maxformationcount-1 do
      [*] = ;                     begin
      [*] = ;                        // 22.10, game D11: the mask index was fixed at 0, and masks[0] is always the
      [*] = ;                        // SMALLEST shape. AddOfficersFormationInf (lib/country.script:2404) puts SIX
      [*] = ;                        // masks into ONE type: LINE15, LINE36, LINE72, LINE120, LINE196, LINE400 (the
      [*] = ;                        // same for SQUARE and KARE), so reading masks[0] could only ever give 15 - and
      [*] = ;                        // the live squad came out LINE15 of 15 men while 143 stood in the cell. Now
      [*] = ;                        // every mask of every type is weighed, and the widest one that fits wins.
      [*] = ;                        for hcm := 0 to gc_country_maxofficersformationmask-1 do
      [*] = ;                        begin
      [*] = ;                        var hfms : String = gCountry[hccid].officers[hfoi].formations[hcj].masks[hcm];
      [*] = ;                        if (hfms <> '') then
      [*] = ;                        begin
      [*] = ;                           var hffi : Integer = _misc_GetFormationIndexBySID(hfms);
      [*] = ;                           if (hffi >= 0) then
      [*] = ;                           begin
      [*] = ;                              var hfbon : Integer = gFormation[hffi].bonusdamage +
      [*] = ;                                   gFormation[hffi].bonusshield +
      [*] = ;                                   gFormation[hffi].bonusdamagehold +
      [*] = ;                                   gFormation[hffi].bonusshieldhold;
      [*] = ;                              var hfcnt : Integer = gFormation[hffi].countunits;
      [*] = ;                              if (hfbon > 0) and (hfcnt < hfneed) then
      [*] = ;                              hfneed := hfcnt;
      [*] = ;                              if (hfbon > 0) and (hfcnt <= hfmen) and (hfcnt > hfbest) then
      [*] = ;                              begin
      [*] = ;                                 hfbest := hfcnt;
      [*] = ;                                 hfform := hffi;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        end;   // masks[hcm] of this formation type
      [*] = ;                     end;
      [*] = ;                     if (hfform < 0) then
      [*] = ;                     begin
      [*] = ;                        // Two different reasons, and they must not be confused:
      [*] = ;                        // 'too few men' is fixable this very tick, 'no formations'
      [*] = ;                        // is not fixable at all.
      [*] = ;                        if (hfneed < 1000000) then
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'FORMATION: too ' +
      [*] = ;                                'few men. The smallest formation with a bonus needs ' +
      [*] = ;                                IntToStr(hfneed) + ', you brought ' + IntToStr(hfmen));
      [*] = ;                           Log('bridge-human: FORMATION - need ' + IntToStr(hfneed) +
      [*] = ;                                ' men, have ' + IntToStr(hfmen));
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'FORMATION: this ' +
      [*] = ;                                'officer has no formation of his own in the country table');
      [*] = ;                           Log('bridge-human: FORMATION - officer has no formations');
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                        hfheld := 0;
      [*] = ;                        for hck := 0 to gIntegerList.GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hfhp : Pointer = _unit_GetTObj(gIntegerList.Get(hck));
      [*] = ;                           if (hfhp <> nil) then
      [*] = ;                           if (TObj(hfhp).bstandground) then
      [*] = ;                           hfheld := hfheld + 1;
      [*] = ;                        end;
      [*] = ;                        var hfsq : Pointer = _player_CreateSquad(hcph, hfform, hfoff,
      [*] = ;                             hfdrum, gIntegerList, True, True);
      [*] = ;                        if (hfsq = nil) then
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'FORMATION: the ' +
      [*] = ;                                'game refused to build the squad');
      [*] = ;                           Log('bridge-human: FORMATION - CreateSquad returned nil');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           // CreateSquad DOES NOT set the formation: it only takes
      [*] = ;                           // the size and the facing out of it (player.script:960).
      [*] = ;                           // The shape itself is applied separately, and without
      [*] = ;                           // this call the squad stands in 'none' with zero bonuses
      [*] = ;                           // - live game 16.09, 54 men in a squad and +0 to
      [*] = ;                           // everything. The engine's own code does the same:
      [*] = ;                           // progresseconomicai.inc:1110.
      [*] = ;                           _player_SetSquadFormation(hcph, TSquad(hfsq).fIndex,
      [*] = ;                                hfform, True, False);
      [*] = ;                           var hfhw : String = '';
      [*] = ;                           if (hca1 = 1) and (hfheld * 2 >= gIntegerList.GetCount) and (hfheld > 0) then
      [*] = ;                           begin
      [*] = ;                              TSquad(hfsq).fStandGround := True;
      [*] = ;                              hfhw := ', ' + IntToStr(hfheld) + ' held ground - squad holds';
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           if (hca1 = 1) then
      [*] = ;                           hfhw := ', ' + IntToStr(hfheld) + ' held ground - squad free';
      [*] = ;                           Log('bridge-human: FORMATION ' + gFormation[hfform].sid +
      [*] = ;                                ' built of ' + IntToStr(gIntegerList.GetCount) + ' men' + hfhw);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'UPGRADE') then
      [*] = ;               begin
      [*] = ;                  // Upgrades without a single _ai_ call. The sid of an upgrade is
      [*] = ;                  // nation prefix + base name ('engmilfood140'), and characters 4..6
      [*] = ;                  // name the building that hosts it - the engine itself decodes it
      [*] = ;                  // that way in _ai_GetBuildingIdByBaseSID. So: match by SUFFIX,
      [*] = ;                  // then find our building of that role.
      [*] = ;                  var hupg : String = ParserGetValueByKeyByHandle(hch, hckey + 'upg');
      [*] = ;                  var huid : Integer = -1;
      [*] = ;                  var husid : String;
      [*] = ;                  var hulen : Integer = StrLength(hupg);
      [*] = ;                  if (hulen > 2) then
      [*] = ;                  for hcj := 0 to gc_country_maxupgradecount-1 do
      [*] = ;                  if (huid < 0) then
      [*] = ;                  begin
      [*] = ;                     var hus : String = gCountry[hccid].upgrade[hcj].id;
      [*] = ;                     if (StrLength(hus) > hulen) then
      [*] = ;                     if (SubStr(hus, StrLength(hus)-hulen+1, hulen) = hupg) then
      [*] = ;                     begin
      [*] = ;                        huid := hcj;
      [*] = ;                        husid := hus;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (huid < 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'UPGRADE ' + hupg +
      [*] = ;                          ': no upgrade with this name for our nation');
      [*] = ;                     Log('bridge-human: UPGRADE ' + hupg + ' - unknown for this nation');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hupart : String = SubStr(husid, 4, 3);
      [*] = ;                     var hurole : Integer = -1;
      [*] = ;                     if (hupart = 'mil') then hurole := gc_ai_unit_mill;
      [*] = ;                     if (hupart = 'cen') then hurole := gc_ai_unit_center;
      [*] = ;                     if (hupart = 'bla') then hurole := gc_ai_unit_smith;
      [*] = ;                     if (hupart = 'bar') then hurole := gc_ai_unit_ba17;
      [*] = ;                     if (hupart = 'sta') then hurole := gc_ai_unit_stable;
      [*] = ;                     if (hupart = 'aca') then hurole := gc_ai_unit_academi;
      [*] = ;                     // 1.11: the 18th-century barracks researches its own steps (bar.* -> ba2.*).
      [*] = ;                     if (hupart = 'ba2') then hurole := gc_ai_unit_ba18;
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     if (hurole >= 0) then
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hugo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hupo : Pointer = _unit_GetTObj(hugo);
      [*] = ;                        if (hupo<>nil) then
      [*] = ;                        if (gObjProp[TObj(hupo).cid][TObj(hupo).id].airole = hurole) then
      [*] = ;                        if (TObj(hupo).bbuilt) then
      [*] = ;                        gIntegerList.Add(hugo);
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount = 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'UPGRADE ' + hupg +
      [*] = ;                             ': the building that researches it is not built');
      [*] = ;                        Log('bridge-human: UPGRADE ' + hupg + ' - host building missing');
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     // The price, so a refusal names a NUMBER. Read straight from the
      [*] = ;                     // nation table by OUR index: _country_GetUpgradeCostBySID skips the
      [*] = ;                     // lookup for index 0 (country.script:760 tests upgid>0).
      [*] = ;                     //
      [*] = ;                     // The check itself stays the engine's. 16.09 I replaced it with my own
      [*] = ;                     // comparison, reading gPlayer[].res as a plain number - and mil.1, worth
      [*] = ;                     // 750 food at 3733 in store, was refused. In this language these fields
      [*] = ;                     // are read through 'not' (block_hstate does exactly that for 'food'),
      [*] = ;                     // so the engine's 'not res >= cost' is correct and mine was not.
      [*] = ;                     var hucf : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_food];
      [*] = ;                     var hucw : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_wood];
      [*] = ;                     var hucs : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_stone];
      [*] = ;                     var hucg : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_gold];
      [*] = ;                     var huci : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_iron];
      [*] = ;                     var hucc : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_coal];
      [*] = ;                     var huprice : String = 'food=' + IntToStr(hucf) + ' wood=' + IntToStr(hucw) +
      [*] = ;                          ' stone=' + IntToStr(hucs) + ' gold=' + IntToStr(hucg) +
      [*] = ;                          ' iron=' + IntToStr(huci) + ' coal=' + IntToStr(hucc);
      [*] = ;                     if (not _unit_CanApplyUpgradeCostBySID(hcph, hccid, husid)) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'UPGRADE ' + hupg +
      [*] = ;                             ': NOT ENOUGH RESOURCES. It costs ' + huprice);
      [*] = ;                        Log('bridge-human: UPGRADE ' + hupg + ' - cannot pay, costs ' + huprice);
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                        _unit_MakeUpgrade(hcph, gIntegerList, huid, True, True);
      [*] = ;                        Log('bridge-human: UPGRADE ' + husid + ' started, costs ' + huprice);
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // --- ATTACK: same file as the AI-side bridge, executed by us ---
      [*] = ;      var hapath : String = '@@OUT@@coss3_atk_P' + IntToStr(plind) + '.dat';
      [*] = ;      if IsFileExists(hapath) then
      [*] = ;      begin
      [*] = ;         var hah : Integer = ParserSelectByKey('br_hatk');
      [*] = ;         if (hah = 0) then
      [*] = ;         hah := ParserCreate('br_hatk');
      [*] = ;         ParserClearByHandle(hah);
      [*] = ;         var haok : Boolean = ParserLoadFromFileByHandle(hah, hapath);
      [*] = ;         DeleteFileStream(hapath);
      [*] = ;         // A LIST OF ORDERS IN ONE FILE (4.10, request of the mac, par.78). Until now
      [*] = ;         // the file carried ONE order and the block obeyed one wave per tick, so
      [*] = ;         // 'the decoy walks back while the main force strikes' was impossible to
      [*] = ;         // express: two orders of one kind in a tick overwrote each other in the
      [*] = ;         // file. The engine never forbade it - _player_SetGroupPosition is per
      [*] = ;         // group, and groups are made by name here - the limit was this file and
      [*] = ;         // this loop.
      [*] = ;         // FORMAT: 'orders' = how many; keys of order i are prefixed '<i>_'.
      [*] = ;         // No 'orders' key means the OLD single-order file with flat keys, and the
      [*] = ;         // bridge still writes those for order 0 - so a new bridge works with an
      [*] = ;         // old block in the game, and a new block with an old bridge.
      [*] = ;         var haon : Integer = ParserGetIntValueByKeyByHandle(hah, 'orders');
      [*] = ;         var hanew : Boolean = (haon > 0);
      [*] = ;         if (not hanew) then
      [*] = ;         haon := 1;
      [*] = ;         // Counters live HERE, not inside the loop: a number declared in a nested
      [*] = ;         // begin does not accumulate (HANDOFF, six army counters, 17.09).
      [*] = ;         var haoi : Integer;
      [*] = ;         var hatk : Integer;
      [*] = ;         var hapre : String;
      [*] = ;         if (haok) then
      [*] = ;         begin
      [*] = ;            var haph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var han : Integer = GetPlayerGameObjectsCountByHandle(haph);
      [*] = ;            // Our own anchor point: the ATTACK file is read outside the command
      [*] = ;            // block, so it cannot borrow its variables. Centre if we have one,
      [*] = ;            // otherwise any object of ours.
      [*] = ;            var hax, haz : Float;
      [*] = ;            var habk : Integer;
      [*] = ;            var haanchor : Boolean = False;
      [*] = ;            for habk := 0 to han-1 do
      [*] = ;            if (not haanchor) then
      [*] = ;            begin
      [*] = ;               var habgo : Integer = GetGameObjectHandleByIndex(habk, haph);
      [*] = ;               var habpo : Pointer = _unit_GetTObj(habgo);
      [*] = ;               if (habpo<>nil) then
      [*] = ;               if (gObjProp[TObj(habpo).cid][TObj(habpo).id].airole = gc_ai_unit_center) then
      [*] = ;               begin
      [*] = ;                  hax := GetGameObjectPositionXByHandle(habgo);
      [*] = ;                  haz := GetGameObjectPositionZByHandle(habgo);
      [*] = ;                  haanchor := True;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (not haanchor) and (han > 0) then
      [*] = ;            begin
      [*] = ;               var haany : Integer = GetGameObjectHandleByIndex(0, haph);
      [*] = ;               hax := GetGameObjectPositionXByHandle(haany);
      [*] = ;               haz := GetGameObjectPositionZByHandle(haany);
      [*] = ;            end;
      [*] = ;            // 'IN THE FIELD' IS A CELL, NOT 60 UNITS (5.10, par.99). In check 5 a heap of
      [*] = ;            // 74 of ours stood in cell (10,10) with the town hall in (12,13): 3.6 cells,
      [*] = ;            // about 58 units. By the old measure it was NOT in the field (further than 60
      [*] = ;            // from the hall), and it did not count as free either, because it stood under
      [*] = ;            // an order - so RETREAT and ENGAGE, which take the FAR ones, could not reach
      [*] = ;            // it, while ATTACK and MOVE take idle men only. The main force was out of
      [*] = ;            // reach of every order, and 'strike the squad next to us' was impossible even
      [*] = ;            // when the decision was right.
      [*] = ;            // The measure is now THE GRID THE MODEL ITSELF NAMES: a man is in the field
      [*] = ;            // when his cell is neither the town hall cell nor one next to it, that is
      [*] = ;            // further than one cell by Chebyshev (32 units and up on a 256 map).
      [*] = ;            // hafn/hafr must match cHmGrid/cHmHome in the state block: what the bridge
      [*] = ;            // REPORTS as away has to be exactly what it CAN order, or the two measures
      [*] = ;            // drift apart again.
      [*] = ;            var hafn : Integer = 16;   // cHmGrid in the state block; grids must match
      [*] = ;            var hafr : Integer = 1;    // cHmHome there: the hall cell and the eight around it
      [*] = ;            var hafw : Integer = GetMapWidth;
      [*] = ;            var hafh : Integer = GetMapHeight;
      [*] = ;            var hafhw : Integer = hafw div 2;
      [*] = ;            var hafhh : Integer = hafh div 2;
      [*] = ;            var hafbx : Integer = floor((hax+hafhw)*hafn/hafw);
      [*] = ;            var hafby : Integer = floor((haz+hafhh)*hafn/hafh);
      [*] = ;            // ONE SOLDIER IS NOT SHARED BY TWO ORDERS of the same tick: whoever is
      [*] = ;            // taken goes into gTmpIntList and is skipped by the orders that follow.
      [*] = ;            // Declared HERE, at the order level, not inside the loop: a scalar declared
      [*] = ;            // in a nested begin does not accumulate (17.09, six army counters read zero
      [*] = ;            // at 208 soldiers).
      [*] = ;            var haheldn : Integer = 0;
      [*] = ;            // DEFENSIVE ATTACK counters (list item 2) live here too, reset per order below.
      [*] = ;            var hadefn : Boolean;
      [*] = ;            var hadefe, hadeft : Integer;
      [*] = ;            var hadefo : Integer;   // holding men OUTSIDE squads and idle: what the second pass can take at most
      [*] = ;            var hadead : Integer;   // corpses met in the first pass (31.10): said aloud, silence is not a proof
      [*] = ;            var hagkeep, hagtot : Integer;   // merge (item 2): remembered men kept / total roll
      [*] = ;            gTmpIntList.Clear;
      [*] = ;            for haoi := 0 to haon-1 do
      [*] = ;            begin
      [*] = ;               hapre := '';
      [*] = ;               if (hanew) then
      [*] = ;               hapre := IntToStr(haoi) + '_';
      [*] = ;         // Mode is read HERE, before the condition that uses it. First try put
      [*] = ;         // the declaration inside the block and the test in its own condition -
      [*] = ;         // a name used before it is declared. The whole Progress tick stopped
      [*] = ;         // compiling, exactly as PROGRESS.md 5.4 describes.
      [*] = ;         var hamode : String = ParserGetValueByKeyByHandle(hah, hapre + 'mode');
      [*] = ;         // WHO (19.09): take only fighters of ONE kind, if the model named it.
      [*] = ;         // Empty means everybody, as before. The names are the same the state
      [*] = ;         // writes in 'fighters': infantry17, musk17, uniq_inf17, dragoon17 - so
      [*] = ;         // the model orders with the word she already reads.
      [*] = ;         // Why at all: the bridge counts the exchange now, and it differs by kind
      [*] = ;         // - 19.09 our pikeman traded 10 to 1 against his, while the musketeer
      [*] = ;         // traded even. Sending everybody drags into the fight those who only
      [*] = ;         // die there.
      [*] = ;         var hawho : String = ParserGetValueByKeyByHandle(hah, hapre + 'who');
      [*] = ;         var hawrole : Integer = -1;
      [*] = ;         // 1.11 (18th century, word of the player): a kind of the 17th century takes its
      [*] = ;         // 18th-century twin too (hawrole2), so 'infantry17' still means 'our pikes' after
      [*] = ;         // cen.1 and every python rule keeps working; the new names select one kind alone.
      [*] = ;         var hawrole2 : Integer = -1;
      [*] = ;         if (hawho = 'infantry17') then hawrole := gc_ai_unit_infantry17;
      [*] = ;         if (hawho = 'infantry17') then hawrole2 := gc_ai_unit_pikeman18;
      [*] = ;         if (hawho = 'musk17') then hawrole := gc_ai_unit_musk17;
      [*] = ;         if (hawho = 'musk17') then hawrole2 := gc_ai_unit_musk18;
      [*] = ;         if (hawho = 'uniq_inf17') then hawrole := gc_ai_unit_uniq_inf17;
      [*] = ;         if (hawho = 'dragoon17') then hawrole := gc_ai_unit_dragoon17;
      [*] = ;         if (hawho = 'dragoon17') then hawrole2 := gc_ai_unit_dragun18;
      [*] = ;         if (hawho = 'pikeman18') then hawrole := gc_ai_unit_pikeman18;
      [*] = ;         if (hawho = 'musk18') then hawrole := gc_ai_unit_musk18;
      [*] = ;         if (hawho = 'dragun18') then hawrole := gc_ai_unit_dragun18;
      [*] = ;         if (hawho = 'reitar') then hawrole := gc_ai_unit_reitar;
      [*] = ;         if (hawho = 'uniq_cav17') then hawrole := gc_ai_unit_uniq_cav17;
      [*] = ;         if (hawho = 'cuirassier') then hawrole := gc_ai_unit_cuirassier;
      [*] = ;         if (hawho = 'hussar') then hawrole := gc_ai_unit_hussar;
      [*] = ;         // 4.11 (207): the foot archer (Turkish archertur, airole gc_ai_unit_archer) - the raider of the mines.
      [*] = ;         if (hawho = 'archer') then hawrole := gc_ai_unit_archer;
      [*] = ;         // RETREAT (18.09): the same order file, third mode. Takes the soldiers
      [*] = ;         // FARTHER than 60 from our centre whatever they are doing - a wave in
      [*] = ;         // the field, wounded or not - and walks them home in default mode.
      [*] = ;         // MOVE could not do it: it takes idle men only, and a fighting wave is
      [*] = ;         // never idle. A player does it with one click on the minimap.
      [*] = ;         var haretreat : Boolean = (hamode = 'retreat');
      [*] = ;         // ENGAGE (18.09): the marching column is INTERCEPTED. Soldiers on a MOVE
      [*] = ;         // order cannot be re-collected by ATTACK (it takes idle men only), so
      [*] = ;         // the column walks on and gets picked apart. This mode takes everybody
      [*] = ;         // farther than 60 from the centre, whatever their order - exactly the
      [*] = ;         // retreat set - and sends them into the ATTACK path instead of home.
      [*] = ;         var haengage : Boolean = (hamode = 'engage');
      [*] = ;         // FACE (5.10, par.98): turn ON THE SPOT, no walking. Until now dirX,dirZ of
      [*] = ;         // every group order was the constant 0,1, so every formation of ours looked
      [*] = ;         // towards +Z of the map whatever it was doing - in check 5, with our base at
      [*] = ;         // (12,13) and his at (1,2), that was towards OUR OWN base, and the player saw
      [*] = ;         // it with his own eyes: they stood with their backs to the enemy. A player
      [*] = ;         // does this with a right-button DRAG, which is the same dirX,dirZ of the same
      [*] = ;         // call (lib/player.script:2292-2390: the drag angle becomes
      [*] = ;         // VectorRotateY(0,0,-1,angle) and goes into WriteMove).
      [*] = ;         // Not _player_StandGroupToPosition: that one TELEPORTS men with
      [*] = ;         // SetGameObjectPositionByHandle, which is scenario placement, not an order.
      [*] = ;         var haface : Boolean = (hamode = 'face');
      [*] = ;         // KITE (26.10): volley and step back. The order only SWITCHES the mode on for a numbered group;
      [*] = ;         // the work is done once a game second by the controller after the order file (see KITE below).
      [*] = ;         // Python ticks every 5 s and names 16-tile cells, while a musketeer has 7.5 tiles between his
      [*] = ;         // minimum range and his maximum and a pikeman closes 1.15 tiles a second - so the second-by-second
      [*] = ;         // part cannot live in python, and the order is just 'these shooters, kite'.
      [*] = ;         var hakite : Boolean = (hamode = 'kite');
      [*] = ;         // NAME OF THE ORDER FOR THE LOG: hamode is EMPTY for an attack (an older
      [*] = ;         // client sends no such key), and pasting it raw gave 'hold released by'
      [*] = ;         // with a double space and no order named at all - seen in the live game
      [*] = ;         // of par.102, in the very lines that proved the measure.
      [*] = ;         var hamw : String = hamode;
      [*] = ;         if (hamw = '') then hamw := 'attack';
      [*] = ;         // HOLD (5.10, par.102, decision of the player). FACE alone lived one tick: it
      [*] = ;         // leads men to the point they already stand on, they arrive at once, the order
      [*] = ;         // empties - and the next ATTACK that takes idle men took them away the same
      [*] = ;         // tick. Measured on the live game of par.98: the group turned, and the
      [*] = ;         // strategy walked it north two cells later.
      [*] = ;         // The engine has the mode a player sets with the squad button:
      [*] = ;         // TObj.bstandground (classes.script:3639), set by
      [*] = ;         // readsquadlistaction.inc:132-146 together with TSquad.fStandGround. A holding
      [*] = ;         // man does not chase (unit.script:7367) and does not walk to a better firing
      [*] = ;         // point (:8064), but DOES search for a victim within his attack radius and
      [*] = ;         // attack it (:8416-8425) - so holding shooters shoot. Any movement order
      [*] = ;         // clears the flag by itself (writemove.inc:120, readorder.inc:62-96), so there
      [*] = ;         // is nothing to clear by hand.
      [*] = ;         // Default is 1: a turn nobody holds is the case that did not work.
      [*] = ;         var hahold : Boolean = True;
      [*] = ;         if (ParserGetValueByKeyByHandle(hah, hapre + 'hold') <> '') then
      [*] = ;         hahold := (ParserGetIntValueByKeyByHandle(hah, hapre + 'hold') <> 0);
      [*] = ;         // ALL (28.10, mac, game D20): the whole army leaves home. ATTACK by count takes idle men
      [*] = ;         // only, and in D20 the exit rule asked for 171 while 143 stood in a LINE120 squad and 33
      [*] = ;         // held ground as the screen: 39 went, were cut off four cells out, and the squad never
      [*] = ;         // moved. With all=1 holding men go with the wave (hold released), and every squad of
      [*] = ;         // ours is sent AS A SQUAD to the same target (_player_SetSquadPosition - the squad keeps
      [*] = ;         // its shape and bonus), hold released the way lib/unit.script does it. Missing key: as before.
      [*] = ;         var haall : Boolean = (ParserGetIntValueByKeyByHandle(hah, hapre + 'all') <> 0);
      [*] = ;         // LIST ITEM 2 (31.10): merge=1 - the remembered roll of the group STAYS and the new men are added to it, the order
      [*] = ;         // goes to the new men only (a counted MOVE used to REPLACE the roll, and the standing men fell out of the group);
      [*] = ;         // arrive=1 - a MOVE sets hold (fStandGround) when the men have ARRIVED, checked every second below, instead of
      [*] = ;         // a FACE hold 20 s later from python that lost the one order slot of the tick. Missing keys: as before.
      [*] = ;         var hamerge : Boolean = (ParserGetIntValueByKeyByHandle(hah, hapre + 'merge') <> 0);
      [*] = ;         var haarrive : Boolean = (ParserGetIntValueByKeyByHandle(hah, hapre + 'arrive') <> 0);
      [*] = ;         // RAID RETREAT (1.11, mac, player's word): ret=N on a numbered ATTACK - N game seconds after the order the living of
      [*] = ;         // the remembered roll walk home to the town hall (move mode default: a walk, not a hunt), checked once a game second
      [*] = ;         // below. Any later order to the same group disarms it. Missing key or 0: as before.
      [*] = ;         var haret : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'ret');
      [*] = ;         // SOURCE CELL (4.11 evening, player's word 'take the lone men standing in the field away'): sx/sy on a counted order -
      [*] = ;         // only men standing IN that cell of the 16x16 grid (hafn, the grid of hafbx above) qualify. A counted RETREAT took the
      [*] = ;         // first N far men in object-list order and would have pulled the wave instead of the straggler. Missing key: as before.
      [*] = ;         var hassrc : Boolean = (ParserGetValueByKeyByHandle(hah, hapre + 'sx') <> '');
      [*] = ;         var hasx : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'sx');
      [*] = ;         var hasy : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'sy');
      [*] = ;         var hasrcn : Integer = 0;
      [*] = ;         var hasqn : Integer = 0;
      [*] = ;         var hasqm : Integer = 0;
      [*] = ;               // Turning in place is not combat, so truce does not forbid it - same
      [*] = ;               // reasoning as for move and retreat.
      [*] = ;               if ((not gbool_peacemode) or (hamode = 'move') or (haretreat) or (haface)) then
      [*] = ;               begin
      [*] = ;            var hawant : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'count');
      [*] = ;            var hatrg : String = ParserGetValueByKeyByHandle(hah, hapre + 'target');
      [*] = ;            // GROUP (4.10, par.78): which army of ours this order is about.
      [*] = ;            // Zero or missing - behave exactly as before, so old hints and
      [*] = ;            // --strategy do not change at all.
      [*] = ;            var hagid : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'group');
      [*] = ;            // Order TO an existing group carries no count: the men are the ones
      [*] = ;            // remembered when the group was made, minus the dead.
      [*] = ;            var hagold : Boolean = (hagid > 0) and (hawant <= 0);
      [*] = ;            // NOT THOSE ALREADY AT THE TARGET (5.11, mac, item 1 of the block list; game.log of live game 2, 4.11): a counted order
      [*] = ;            // took the first N idle men in object-list order - the oldest, i.e. the fist standing at the target - and 'led' them
      [*] = ;            // into their own cell three times (5:34, 6:24, 7:12), while the recruits piled at the barracks. A counted ATTACK/MOVE
      [*] = ;            // into a cell is picked in TWO PASSES: first everybody NOT standing in the target cell, then, if the count is short,
      [*] = ;            // those in it (the old order). The count is always met when the men exist; what was deferred and refilled is logged.
      [*] = ;            // Orders to a remembered group, ALL, RETREAT/ENGAGE/FACE/KITE and targets other than a cell: as before.
      [*] = ;            var hask : Boolean = (hatrg = 'cell') and (not haall) and (not hagold) and (not haretreat) and (not haengage) and (not haface) and (not hakite);
      [*] = ;            var hanear : Integer = 0;
      [*] = ;            var hanfill : Integer = 0;
      [*] = ;            var hapass : Integer;
      [*] = ;            var haskcx : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'cx');
      [*] = ;            var haskcy : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'cy');
      [*] = ;            // MOVE: the same order file, only the mode differs. A player moves his
      [*] = ;            // troops wherever he likes with a click and is not obliged to send them
      [*] = ;            // into battle; the bot had ATTACK and nothing else, so a manoeuvre -
      [*] = ;            // stand aside, take a place in advance - was physically impossible.
      [*] = ;            // Empty mode means attack: an older client sends no such key.
      [*] = ;            var hak : Integer;
      [*] = ;            // Idle soldiers only: a unit already marching is left alone, otherwise
      [*] = ;            // a new order regroups the wave and it stalls - learned the hard way.
      [*] = ;            hadefo := 0;   // reset BEFORE the first pass that counts it (30.10 evening: reset stood after it, Ho printed 0 at 171 taken)
      [*] = ;            hadead := 0;
      [*] = ;            hagkeep := 0;
      [*] = ;            hagtot := 0;
      [*] = ;            gIntegerList.Clear;
      [*] = ;            for hapass := 0 to 1 do
      [*] = ;            for hak := 0 to han-1 do
      [*] = ;            if (gIntegerList.GetCount < hawant) then
      [*] = ;            begin
      [*] = ;               var hago : Integer = GetGameObjectHandleByIndex(hak, haph);
      [*] = ;               var hapo : Pointer = _unit_GetTObj(hago);
      [*] = ;               if (hapo<>nil) then
      [*] = ;               if (TObj(hapo).bdead) and (hapass = 0) then
      [*] = ;               hadead := hadead + 1;
      [*] = ;               if (hapo<>nil) then
      [*] = ;               // CORPSES STAY IN THE PLAYER'S OBJECT LIST (31.10, 76 'roll cleaned' lines, 16 with >= 50% dead a second after the pick): dead men are not ours to count or to order. Wave pick.
      [*] = ;               if (not TObj(hapo).bdead) then
      [*] = ;               begin
      [*] = ;                  var hau : Integer = gObjProp[TObj(hapo).cid][TObj(hapo).id].usage;
      [*] = ;                  if (not gObjProp[TObj(hapo).cid][TObj(hapo).id].bbuilding) then
      [*] = ;                  if (hau <> gc_obj_usage_peasant) and (hau <> gc_obj_usage_none) then
      [*] = ;                  begin
      [*] = ;                     // Idle men for ATTACK and MOVE; the FAR ones, idle or not, for RETREAT,
      [*] = ;                     // ENGAGE and FACE: a formation worth turning is one that stands in the
      [*] = ;                     // field, and it is never idle.
      [*] = ;                     // HOLDING MEN ARE NOT AVAILABLE (par.102): a man told to hold his ground is
      [*] = ;                     // on duty, not idle, and the whole point of hold is that the next order by
      [*] = ;                     // count does not dissolve the formation. They are released only by an order
      [*] = ;                     // ADDRESSED TO THEIR GROUP (count 0, group N), which takes no selection at
      [*] = ;                     // all and reads the remembered roll instead. Counted and said aloud below:
      [*] = ;                     // a man refused in silence is indistinguishable from a man who was not there.
      [*] = ;                     var hatake2 : Boolean = False;
      [*] = ;                     var hahled : Boolean = TObj(hapo).bstandground;
      [*] = ;                     if (haretreat) or (haengage) or (haface) then
      [*] = ;                     begin
      [*] = ;                        var hafux : Integer = floor((GetGameObjectPositionXByHandle(hago)+hafhw)*hafn/hafw);
      [*] = ;                        var hafuy : Integer = floor((GetGameObjectPositionZByHandle(hago)+hafhh)*hafn/hafh);
      [*] = ;                        var hafdc : Integer = Round(Abs(hafux - hafbx));
      [*] = ;                        var hafdy : Integer = Round(Abs(hafuy - hafby));
      [*] = ;                        // Chebyshev distance without a Max: the larger of the two.
      [*] = ;                        if (hafdc < hafdy) then hafdc := hafdy;
      [*] = ;                        if (hafdc > hafr) then hatake2 := True;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (TObj(hapo).orders[0].itype = gc_obj_order_type_none) then hatake2 := True;
      [*] = ;                     // SECOND PASS (5.11, item 1): a man taken in the first pass is not taken again; counters below see new candidates only.
      [*] = ;                     if (hatake2) and (hapass = 1) and (gIntegerList.GetCount > 0) then
      [*] = ;                     for hatk := 0 to gIntegerList.GetCount-1 do
      [*] = ;                     if (gIntegerList.Get(hatk) = hago) then
      [*] = ;                     hatake2 := False;
      [*] = ;                     // ALREADY AT THE TARGET (5.11, item 1): skip a man standing in the target cell or next to it.
      [*] = ;                     if (hatake2) and (hask) and (hapass = 0) then
      [*] = ;                     begin
      [*] = ;                     var haskx : Integer = floor((GetGameObjectPositionXByHandle(hago)+hafhw)*hafn/hafw);
      [*] = ;                     var hasky : Integer = floor((GetGameObjectPositionZByHandle(hago)+hafhh)*hafn/hafh);
      [*] = ;                     var haskd : Integer = Round(Abs(haskx - haskcx));
      [*] = ;                     var haskdy : Integer = Round(Abs(hasky - haskcy));
      [*] = ;                     if (haskd < haskdy) then haskd := haskdy;
      [*] = ;                     if (haskd = 0) then
      [*] = ;                     begin
      [*] = ;                     hatake2 := False;
      [*] = ;                     hanear := hanear + 1;
      [*] = ;                     end;
      [*] = ;                     end;
      [*] = ;                     // SOURCE CELL filter (4.11): with sx/sy the man must stand in that cell; counted below, said aloud after the pick.
      [*] = ;                     if (hatake2) and (hassrc) then
      [*] = ;                     begin
      [*] = ;                     var hasux : Integer = floor((GetGameObjectPositionXByHandle(hago)+hafhw)*hafn/hafw);
      [*] = ;                     var hasuy : Integer = floor((GetGameObjectPositionZByHandle(hago)+hafhh)*hafn/hafh);
      [*] = ;                     if (hasux <> hasx) or (hasuy <> hasy) then hatake2 := False;
      [*] = ;                     if (hatake2) then hasrcn := hasrcn + 1;
      [*] = ;                     end;
      [*] = ;                     // The kind filter is applied LAST, after the idle/far test: the two
      [*] = ;                     // questions are separate, and mixing them would hide which one
      [*] = ;                     // refused the man.
      [*] = ;                     if (hatake2) and (hawrole >= 0) then
      [*] = ;                     if (gObjProp[TObj(hapo).cid][TObj(hapo).id].airole <> hawrole) and (gObjProp[TObj(hapo).cid][TObj(hapo).id].airole <> hawrole2) then
      [*] = ;                     hatake2 := False;
      [*] = ;                     // ALL: men of a squad go as squads (below), holding men outside squads go with the wave
      [*] = ;                     if (hatake2) and (haall) and (TObj(hapo).squad >= 0) then
      [*] = ;                     begin
      [*] = ;                        hatake2 := False;
      [*] = ;                     end;
      [*] = ;                     if (hatake2) and (hahled) and (not haall) then
      [*] = ;                     begin
      [*] = ;                        hatake2 := False;
      [*] = ;                        if (hapass = 0) then haheldn := haheldn + 1;
      [*] = ;                        if (hapass = 0) and (TObj(hapo).squad < 0) then hadefo := hadefo + 1;
      [*] = ;                     end;
      [*] = ;                     // Already taken by an earlier order of THIS tick - skip.
      [*] = ;                     if (hatake2) and (gTmpIntList.GetCount > 0) then
      [*] = ;                     for hatk := 0 to gTmpIntList.GetCount-1 do
      [*] = ;                     if (gTmpIntList.Get(hatk) = hago) then
      [*] = ;                     hatake2 := False;
      [*] = ;                     if (hatake2) then gIntegerList.Add(hago);
      [*] = ;                     if (hatake2) and (hapass = 1) then hanfill := hanfill + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // WAVE PICK SAID ALOUD (31.10, Windows: 'roll cleaned' prints only when something was dropped, so a working
      [*] = ;            // filter would be proven by silence - and silence has other causes). Alive taken by the first pass, corpses met.
      [*] = ;            if (hassrc) then
      [*] = ;            Log('bridge-human: source cell ' + IntToStr(hasx) + ',' + IntToStr(hasy) + ': ' + IntToStr(hasrcn) + ' men taken from it');
      [*] = ;            if (hask) and (hanear > 0) then
      [*] = ;            Log('bridge-human: pick deferred ' + IntToStr(hanear) + ' men standing in the target cell ' + IntToStr(haskcx) + ',' + IntToStr(haskcy) + ', ' + IntToStr(hanfill) + ' of them taken to fill the count');
      [*] = ;            Log('bridge-human: wave pick at ' + IntToStr(Round(GetGameTime)) + ' s: ' + IntToStr(gIntegerList.GetCount) + ' alive taken, ' + IntToStr(hadead) + ' dead skipped, ' + IntToStr(haheldn) + ' holding refused');
      [*] = ;            // MIRRORED INTO THE STATE (31.10, Windows: on Windows the game writes no log with bridge lines; in the container there is no
      [*] = ;            // battle - a measure named by a log line is judged nowhere). Last pick: time, alive, dead, refused -> hstate pick_*.
      [*] = ;            var hapkp : Integer = ParserSelectByKey('br_hdef');
      [*] = ;            if (hapkp <> 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hapkp, 'pkt' + IntToStr(plind), Round(GetGameTime));
      [*] = ;               ParserSetIntValueByKeyByHandle(hapkp, 'pka' + IntToStr(plind), gIntegerList.GetCount);
      [*] = ;               ParserSetIntValueByKeyByHandle(hapkp, 'pkd' + IntToStr(plind), hadead);
      [*] = ;               ParserSetIntValueByKeyByHandle(hapkp, 'pkr' + IntToStr(plind), haheldn);
      [*] = ;            end;
      [*] = ;            // Where to go. The model chooses: peasants (the objective), base, or army.
      [*] = ;            var hatx, hatz : Float;
      [*] = ;            // WALL AS A TARGET (1.11, player's word: 'point the army's attack at the palisade').
      [*] = ;            // Why a separate target and not just a cell: a cell is a COORDINATE, and the block turns
      [*] = ;            // it into _player_SetGroupPosition - 'go stand at this point'. A sealed palisade has no
      [*] = ;            // path through it, so the army stood at home and nobody ever touched the wall: in the live
      [*] = ;            // game of 1.11 all twelve wall cells stayed at hp 100 while 158 men were under orders.
      [*] = ;            // A wall must be ATTACKED AS AN OBJECT, and that needs a handle - which python cannot have.
      [*] = ;            // Declared at block level on purpose: a scalar declared inside a nested begin does not
      [*] = ;            // survive it (bought 17.09 by six army counters that read zero at 208 soldiers).
      [*] = ;            // NO INITIALISER HERE, and that was bought by the live game of 1.11. With
      [*] = ;            // 'var hawallh : Integer = 0;' the handle never reached the order site: the order did go
      [*] = ;            // out (log: ATTACK 1 target=wall at -2.5,4.5 - the position of the wall OBJECT itself),
      [*] = ;            // yet 'if (hawallh > 0)' never fired. Right above stands 'var hatx, hatz : Float;' WITHOUT
      [*] = ;            // an initialiser, and the very same assignments out of the nested loops do arrive. So the
      [*] = ;            // initialiser looks replayed on entering the block while a plain write survives.
      [*] = ;            // The zero is set as a STATEMENT, not as an initialiser.
      [*] = ;            var hawallh : Integer;
      [*] = ;            hawallh := 0;
      [*] = ;            // THE REMEMBERED COMPOSITION of group hagid. The selection loop above
      [*] = ;            // added nobody (its guard is count, and an order to a group has none),
      [*] = ;            // so the list is empty and we fill it from the parser.
      [*] = ;            if (hagold) then
      [*] = ;            begin
      [*] = ;               var hagp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;               if (hagp <> 0) then
      [*] = ;               begin
      [*] = ;                  var hagn : Integer = ParserGetIntValueByKeyByHandle(hagp, 'g' + IntToStr(hagid) + '_n');
      [*] = ;                  for hak := 0 to hagn-1 do
      [*] = ;                  begin
      [*] = ;                     var hagh : Integer = ParserGetIntValueByKeyByHandle(hagp, 'g' + IntToStr(hagid) + '_h' + IntToStr(hak));
      [*] = ;                     if (hagh <> 0) then
      [*] = ;                     begin
      [*] = ;                        var haghp : Pointer = _unit_GetTObj(hagh);
      [*] = ;                        // Dead men are dropped silently here and loudly below: the
      [*] = ;                        // count that went into the game is written to the log.
      [*] = ;                        if (haghp<>nil) then
      [*] = ;                        if (not TObj(haghp).bdead) then
      [*] = ;                        gIntegerList.Add(hagh);
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               Log('bridge-human: GROUP ' + IntToStr(hagid) + ' order to ' +
      [*] = ;                   IntToStr(gIntegerList.GetCount) + ' remembered soldiers');
      [*] = ;            end;
      [*] = ;            var hafound : Boolean = False;
      [*] = ;            var habest : Float = 1000000;
      [*] = ;            var hapl : Integer;
      [*] = ;            for hapl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;            if (gPlayer[hapl].bexists) and (hapl <> plind) then
      [*] = ;            if ((gPlayer[plind].enemyPlMask and gPlayer[hapl].myPlMask) <> 0) then
      [*] = ;            begin
      [*] = ;               var haeph : Integer = GetPlayerHandleByIndex(hapl);
      [*] = ;               var haen : Integer = GetPlayerGameObjectsCountByHandle(haeph);
      [*] = ;               var haj : Integer;
      [*] = ;               for haj := 0 to haen-1 do
      [*] = ;               begin
      [*] = ;                  var haeg : Integer = GetGameObjectHandleByIndex(haj, haeph);
      [*] = ;                  var haep : Pointer = _unit_GetTObj(haeg);
      [*] = ;                  if (haep<>nil) then
      [*] = ;                  // dead enemies are not 'enemy soldiers within 2 cells' (31.10)
      [*] = ;                  if (not TObj(haep).bdead) then
      [*] = ;                  begin
      [*] = ;                     var haeu : Integer = gObjProp[TObj(haep).cid][TObj(haep).id].usage;
      [*] = ;                     var haeb : Boolean = gObjProp[TObj(haep).cid][TObj(haep).id].bbuilding;
      [*] = ;                     var hatake : Boolean = False;
      [*] = ;                     if (hatrg = 'peasants') and (haeu = gc_obj_usage_peasant) then hatake := True;
      [*] = ;                     if (hatrg <> 'peasants') and (hatrg <> 'wall') and (haeb) then hatake := True;
      [*] = ;                     // TARGET 'wall' (1.11, player's word 'point the army's attack at the palisade'):
      [*] = ;                     // ONLY walls, and the HANDLE is remembered - a wall must be attacked as an OBJECT,
      [*] = ;                     // because a position order is a move and a sealed palisade has no path through it.
      [*] = ;                     // Done in THIS loop on purpose: a separate loop of mine set the handle and the
      [*] = ;                     // position came from here anyway - two paths for one answer, and the handle stayed 0.
      [*] = ;                     if (hatrg = 'wall') then
      [*] = ;                     if (haeu = gc_obj_usage_weakwall) or (haeu = gc_obj_usage_hardwall) then
      [*] = ;                     hatake := True;
      [*] = ;                     if (hatake) then
      [*] = ;                     begin
      [*] = ;                        var haex : Float = GetGameObjectPositionXByHandle(haeg);
      [*] = ;                        var haez : Float = GetGameObjectPositionZByHandle(haeg);
      [*] = ;                        var had : Float = VectorDistance(haex, 0, haez, hax, 0, haz);
      [*] = ;                        if (had < habest) then
      [*] = ;                        begin
      [*] = ;                           habest := had;
      [*] = ;                           hatx := haex;
      [*] = ;                           hatz := haez;
      [*] = ;                           hafound := True;
      [*] = ;                           if (hatrg = 'wall') then
      [*] = ;                           hawallh := haeg;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // 'cell' is a COORDINATE target: the model names a cell of the same 16x16
      [*] = ;            // grid that reaches it in the state as frow lines. There were four targets
      [*] = ;            // before (peasants, base, army, home), and every one means 'go to the
      [*] = ;            // nearest such thing'; taking the fist around, or massing it away from the
      [*] = ;            // base, was impossible, and the map stayed mute: 0 cells named in 644 ticks.
      [*] = ;            // The cell resolves to the CENTRE of its square, else the squad walks to a corner.
      [*] = ;            if (hatrg = 'cell') then
      [*] = ;            begin
      [*] = ;               var hacn : Integer = 16;   // cHmGrid in the state block; grids must match
      [*] = ;               var hacx : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'cx');
      [*] = ;               var hacy : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'cy');
      [*] = ;               if (hacx < 0) then hacx := 0;
      [*] = ;               if (hacy < 0) then hacy := 0;
      [*] = ;               if (hacx > hacn-1) then hacx := hacn-1;
      [*] = ;               if (hacy > hacn-1) then hacy := hacn-1;
      [*] = ;               var hacw : Integer = GetMapWidth;
      [*] = ;               var hach : Integer = GetMapHeight;
      [*] = ;               hatx := (hacx + 0.5) * hacw / hacn - hacw div 2;
      [*] = ;               hatz := (hacy + 0.5) * hach / hacn - hach div 2;
      [*] = ;               hafound := True;
      [*] = ;            end;
      [*] = ;            // 'home' is our own anchor: the only target that needs no enemy at all.
      [*] = ;            // TARGET 'group' (4.10, par.78): go to ANOTHER army of ours, named by
      [*] = ;            // gid, and merge into it on arrival. The place of that group is its
      [*] = ;            // men's average - the same reading the state block does, and the only
      [*] = ;            // one available: the engine cannot be asked where a group is.
      [*] = ;            if (hatrg = 'group') then
      [*] = ;            begin
      [*] = ;               var hatgid : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'gid');
      [*] = ;               var hatgp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;               if (hatgid > 0) and (hatgp <> 0) then
      [*] = ;               begin
      [*] = ;                  var hatgn : Integer = ParserGetIntValueByKeyByHandle(hatgp, 'g' + IntToStr(hatgid) + '_n');
      [*] = ;                  var hatsx : Float = 0;
      [*] = ;                  var hatsz : Float = 0;
      [*] = ;                  var hatliv : Integer = 0;
      [*] = ;                  for hak := 0 to hatgn-1 do
      [*] = ;                  begin
      [*] = ;                     var hath : Integer = ParserGetIntValueByKeyByHandle(hatgp, 'g' + IntToStr(hatgid) + '_h' + IntToStr(hak));
      [*] = ;                     if (hath <> 0) then
      [*] = ;                     begin
      [*] = ;                        var hathp : Pointer = _unit_GetTObj(hath);
      [*] = ;                        if (hathp<>nil) then
      [*] = ;                        if (not TObj(hathp).bdead) then
      [*] = ;                        begin
      [*] = ;                           hatsx := hatsx + GetGameObjectPositionXByHandle(hath);
      [*] = ;                           hatsz := hatsz + GetGameObjectPositionZByHandle(hath);
      [*] = ;                           hatliv := hatliv + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hatliv > 0) then
      [*] = ;                  begin
      [*] = ;                     hatx := hatsx / hatliv;
      [*] = ;                     hatz := hatsz / hatliv;
      [*] = ;                     hafound := True;
      [*] = ;                     // WHO WE ARE WALKING TO is remembered: the merge itself happens
      [*] = ;                     // in the state block, which looks at every group each tick.
      [*] = ;                     if (hagid > 0) then
      [*] = ;                     ParserSetIntValueByKeyByHandle(hatgp, 'g' + IntToStr(hagid) + '_to', hatgid);
      [*] = ;                     Log('bridge-human: GROUP ' + IntToStr(hagid) + ' walks to group ' +
      [*] = ;                         IntToStr(hatgid) + ' (' + IntToStr(hatliv) + ' men there)');
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hatrg = 'home') then
      [*] = ;            begin
      [*] = ;               hatx := hax;
      [*] = ;               hatz := haz;
      [*] = ;               hafound := True;
      [*] = ;            end;
      [*] = ;            // FACE NEEDS NO TARGET (5.10, par.98): turning in place needs no enemy and no
      [*] = ;            // point to walk to, so it must not be blocked by 'target found' - a bot with
      [*] = ;            // nobody in sight would have been unable to turn at all.
      [*] = ;            // DEFENSIVE ATTACK (30.10 evening, mac, list item 2; Poland game 12:47-13:08): python's ATTACK by number at his
      [*] = ;            // camp 4 cells from our town hall was refused for the 77 holding men and 27 went. Here the block itself: the
      [*] = ;            // target is within 5 cells of our town hall (Chebyshev, cell = map/16) AND at least 5 enemy soldiers stand
      [*] = ;            // within 2 cells of the target -> the holding men outside squads are taken into the wave after all (second
      [*] = ;            // pass, same filters as above minus the hold refusal), their hold released before the move exactly as ALL
      [*] = ;            // does. Switch atkdef<p> in br_hdef (DEFEND a2), default 1; 0 = as before. Said aloud either way.
      [*] = ;            hadefn := False;
      [*] = ;            hadefe := 0;
      [*] = ;            hadeft := 0;
      [*] = ;            if (hafound) and (haheldn > 0) and (not haall) and (not haretreat) and (not haengage) and (not haface) and (not hakite) and (hamode <> 'move') then
      [*] = ;            begin
      [*] = ;               var hadefp : Integer = ParserSelectByKey('br_hdef');
      [*] = ;               var hadefsw : Integer = 1;
      [*] = ;               if (hadefp <> 0) then
      [*] = ;               if (ParserGetValueByKeyByHandle(hadefp, 'atkdef' + IntToStr(plind)) <> '') then
      [*] = ;               hadefsw := ParserGetIntValueByKeyByHandle(hadefp, 'atkdef' + IntToStr(plind));
      [*] = ;               var hadefr : Float = 5.0 * GetMapWidth / 16.0;
      [*] = ;               var hadefr2 : Float = 2.0 * GetMapWidth / 16.0;
      [*] = ;               var hadefdx : Float = hatx - hax;
      [*] = ;               var hadefdz : Float = hatz - haz;
      [*] = ;               if (hadefsw = 1) and (hadefdx <= hadefr) and (hadefdx >= -hadefr) and (hadefdz <= hadefr) and (hadefdz >= -hadefr) then
      [*] = ;               begin
      [*] = ;                  var hadefpl : Integer;
      [*] = ;                  for hadefpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;                  if (gPlayer[hadefpl].bexists) and (hadefpl <> plind) then
      [*] = ;                  if ((gPlayer[plind].enemyPlMask and gPlayer[hadefpl].myPlMask) <> 0) then
      [*] = ;                  begin
      [*] = ;                     var hadefph : Integer = GetPlayerHandleByIndex(hadefpl);
      [*] = ;                     var hadefoc : Integer = GetPlayerGameObjectsCountByHandle(hadefph);
      [*] = ;                     var hadefj : Integer;
      [*] = ;                     for hadefj := 0 to hadefoc-1 do
      [*] = ;                     begin
      [*] = ;                        var hadefgo : Integer = GetGameObjectHandleByIndex(hadefj, hadefph);
      [*] = ;                        var hadefpo : Pointer = _unit_GetTObj(hadefgo);
      [*] = ;                        if (hadefpo<>nil) then
      [*] = ;                        if (not TObj(hadefpo).bdead) then
      [*] = ;                        begin
      [*] = ;                           var hadefu : Integer = gObjProp[TObj(hadefpo).cid][TObj(hadefpo).id].usage;
      [*] = ;                           if (hadefu = gc_obj_usage_lightinfantry) or (hadefu = gc_obj_usage_weak) or (hadefu = gc_obj_usage_grenadier) or
      [*] = ;                              (hadefu = gc_obj_usage_shooter) or (hadefu = gc_obj_usage_archer) or (hadefu = gc_obj_usage_fasthorse) or
      [*] = ;                              (hadefu = gc_obj_usage_hardhorse) or (hadefu = gc_obj_usage_horseshooter) then
      [*] = ;                           begin
      [*] = ;                              var hadefex : Float = GetGameObjectPositionXByHandle(hadefgo) - hatx;
      [*] = ;                              var hadefez : Float = GetGameObjectPositionZByHandle(hadefgo) - hatz;
      [*] = ;                              if (hadefex <= hadefr2) and (hadefex >= -hadefr2) and (hadefez <= hadefr2) and (hadefez >= -hadefr2) then
      [*] = ;                              hadefe := hadefe + 1;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hadefe >= 5) then
      [*] = ;                  hadefn := True;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hadefn) then
      [*] = ;            begin
      [*] = ;               // Second pass: holding men outside squads, idle, of the asked kind, not taken by an earlier order of this tick.
      [*] = ;               for hak := 0 to han-1 do
      [*] = ;               if (gIntegerList.GetCount < hawant) then
      [*] = ;               begin
      [*] = ;                  var hadfgo : Integer = GetGameObjectHandleByIndex(hak, haph);
      [*] = ;                  var hadfpo : Pointer = _unit_GetTObj(hadfgo);
      [*] = ;                  if (hadfpo<>nil) then
      [*] = ;                  if (not TObj(hadfpo).bdead) then
      [*] = ;                  if (not gObjProp[TObj(hadfpo).cid][TObj(hadfpo).id].bbuilding) then
      [*] = ;                  if (TObj(hadfpo).bstandground) and (TObj(hadfpo).squad < 0) then
      [*] = ;                  if (TObj(hadfpo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                  begin
      [*] = ;                     var hadfu : Integer = gObjProp[TObj(hadfpo).cid][TObj(hadfpo).id].usage;
      [*] = ;                     var hadftk : Boolean = (hadfu <> gc_obj_usage_peasant) and (hadfu <> gc_obj_usage_none);
      [*] = ;                     if (hadftk) and (hawrole >= 0) then
      [*] = ;                     if (gObjProp[TObj(hadfpo).cid][TObj(hadfpo).id].airole <> hawrole) and (gObjProp[TObj(hadfpo).cid][TObj(hadfpo).id].airole <> hawrole2) then
      [*] = ;                     hadftk := False;
      [*] = ;                     if (hadftk) and (gTmpIntList.GetCount > 0) then
      [*] = ;                     for hatk := 0 to gTmpIntList.GetCount-1 do
      [*] = ;                     if (gTmpIntList.Get(hatk) = hadfgo) then
      [*] = ;                     hadftk := False;
      [*] = ;                     if (hadftk) then
      [*] = ;                     begin
      [*] = ;                        gIntegerList.Add(hadfgo);
      [*] = ;                        hadeft := hadeft + 1;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               Log('bridge-human: ' + hamw + ' home defence - target ' + FloatToStr(hatx) + ',' + FloatToStr(hatz) + ' within 5 cells of the town hall, ' +
      [*] = ;                   IntToStr(hadefe) + ' enemy soldiers within 2 cells of it: ' + IntToStr(hadeft) + ' of ' + IntToStr(hadefo) + ' holding soldiers outside squads taken (' + IntToStr(haheldn) + ' holding in all), hold released');
      [*] = ;               // mirrored into the state (31.10): last defensive gate -> hstate hdef_t / hdef_taken / hdef_outside / hdef_enemy
      [*] = ;               var hadmp : Integer = ParserSelectByKey('br_hdef');   // own handle: hadefp lives in another begin..end
      [*] = ;               if (hadmp <> 0) then
      [*] = ;               begin
      [*] = ;                  ParserSetIntValueByKeyByHandle(hadmp, 'hdt' + IntToStr(plind), Round(GetGameTime));
      [*] = ;                  ParserSetIntValueByKeyByHandle(hadmp, 'hdk' + IntToStr(plind), hadeft);
      [*] = ;                  ParserSetIntValueByKeyByHandle(hadmp, 'hdo' + IntToStr(plind), hadefo);
      [*] = ;                  ParserSetIntValueByKeyByHandle(hadmp, 'hde' + IntToStr(plind), hadefe);
      [*] = ;               end;
      [*] = ;            end
      [*] = ;            else
      [*] = ;            // Said BEFORE the order goes out: the number refused for holding explains a
      [*] = ;            // short wave, and silence here would look like 'there was nobody'.
      [*] = ;            if (haheldn > 0) then
      [*] = ;            Log('bridge-human: ' + hamw + ' skipped ' + IntToStr(haheldn) +
      [*] = ;                ' holding soldiers (order them by group number to release)');
      [*] = ;            if ((hafound) or (haface) or (hakite)) and (gIntegerList.GetCount > 0) then
      [*] = ;            begin
      [*] = ;               // ONE GROUP PER WAVE. The name used to be the same for every wave, and
      [*] = ;               // GroupClearGameObjectsByHandle threw out of it those ALREADY MARCHING:
      [*] = ;               // the first wave lost its group and its order the moment the second one
      [*] = ;               // left. The numbers show it plainly - 14.09, nine games: 35 waves, 1139
      [*] = ;               // soldiers sent, zero enemy peasants killed AND zero losses of our own.
      [*] = ;               // The army went out and never arrived. HANDOFF describes the same thing
      [*] = ;               // on the AI side, where the cause sat elsewhere.
      [*] = ;               // Eight names in a circle: no more waves than that live at once.
      [*] = ;               // A NUMBERED group keeps its own name, so an order to it finds the
      [*] = ;               // same group object; a nameless order keeps the old wave slots.
      [*] = ;               var hagname : String = 'coss3_wave_' + IntToStr(Round(GetGameTime) mod 8) + '_' + IntToStr(haoi);
      [*] = ;               if (hagid > 0) then
      [*] = ;               hagname := 'coss3_grp_' + IntToStr(hagid);
      [*] = ;               var hagr : Integer = _misc_GetOrCreateGroupByName(haph, hagname);
      [*] = ;               GroupClearGameObjectsByHandle(hagr);
      [*] = ;               for hak := 0 to gIntegerList.GetCount-1 do
      [*] = ;               GroupAddGameObjectByHandle(hagr, gIntegerList.Get(hak));
      [*] = ;               _group_Initialize(hagr, nil);
      [*] = ;               // REMEMBER WHO IS IN THE GROUP (only when it is being made: an
      [*] = ;               // order to an existing group must not rewrite its roll).
      [*] = ;               if (hagid > 0) and (not hagold) then
      [*] = ;               begin
      [*] = ;                  var hagsp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;                  if (hagsp = 0) then
      [*] = ;                  hagsp := ParserCreate('br_hgrp');
      [*] = ;                  hagtot := gIntegerList.GetCount;
      [*] = ;                  if (hamerge) then
      [*] = ;                  begin
      [*] = ;                     // MERGE: read the old roll first (all of it), then write - writing while reading would clobber unread keys
      [*] = ;                     var hagon : Integer = ParserGetIntValueByKeyByHandle(hagsp, 'g' + IntToStr(hagid) + '_n');
      [*] = ;                     var hagts : Integer = gTmpIntList.GetCount;
      [*] = ;                     var hagk2 : Integer;
      [*] = ;                     for hagk2 := 0 to hagon-1 do
      [*] = ;                     begin
      [*] = ;                        var hagoh : Integer = ParserGetIntValueByKeyByHandle(hagsp, 'g' + IntToStr(hagid) + '_h' + IntToStr(hagk2));
      [*] = ;                        var hagop : Pointer = _unit_GetTObj(hagoh);
      [*] = ;                        if (hagoh <> 0) and (hagop <> nil) then
      [*] = ;                        if (not TObj(hagop).bdead) then
      [*] = ;                        begin
      [*] = ;                           var hagdup : Boolean = False;
      [*] = ;                           var hagk3 : Integer;
      [*] = ;                           for hagk3 := 0 to gIntegerList.GetCount-1 do
      [*] = ;                           if (gIntegerList.Get(hagk3) = hagoh) then hagdup := True;
      [*] = ;                           if (not hagdup) then
      [*] = ;                           begin
      [*] = ;                              gTmpIntList.Add(hagoh);
      [*] = ;                              hagkeep := hagkeep + 1;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     for hagk2 := 0 to hagkeep-1 do
      [*] = ;                     ParserSetIntValueByKeyByHandle(hagsp, 'g' + IntToStr(hagid) + '_h' + IntToStr(gIntegerList.GetCount + hagk2), gTmpIntList.Get(hagts + hagk2));
      [*] = ;                     hagtot := gIntegerList.GetCount + hagkeep;
      [*] = ;                  end;
      [*] = ;                  ParserSetIntValueByKeyByHandle(hagsp, 'g' + IntToStr(hagid) + '_n', hagtot);
      [*] = ;                  for hak := 0 to gIntegerList.GetCount-1 do
      [*] = ;                  ParserSetIntValueByKeyByHandle(hagsp, 'g' + IntToStr(hagid) + '_h' + IntToStr(hak), gIntegerList.Get(hak));
      [*] = ;                  if (hamerge) then
      [*] = ;                  Log('bridge-human: GROUP ' + IntToStr(hagid) + ' roll merged: ' + IntToStr(hagkeep) + ' kept + ' +
      [*] = ;                      IntToStr(gIntegerList.GetCount) + ' new = ' + IntToStr(hagtot))
      [*] = ;                  else
      [*] = ;                  Log('bridge-human: GROUP ' + IntToStr(hagid) + ' made of ' +
      [*] = ;                      IntToStr(gIntegerList.GetCount) + ' soldiers');
      [*] = ;               end;
      [*] = ;               // MODE OF THE GROUP, written for EVERY order with a number, not only
      [*] = ;               // when the group is made. It was inside the 'made' branch at first,
      [*] = ;               // and the live game showed the lie at once: group 1 was ordered home,
      [*] = ;               // walked home, and the state still said mode 1 (walking) instead of 2
      [*] = ;               // (retreating), because that was its mode at birth. 0 attack, 1 move,
      [*] = ;               // 2 retreat, 3 engage.
      [*] = ;               if (hagid > 0) then
      [*] = ;               begin
      [*] = ;                  var hagmp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;                  if (hagmp = 0) then
      [*] = ;                  hagmp := ParserCreate('br_hgrp');
      [*] = ;                  // MODE 4 = HOLDS (par.102). Read the OLD mode first: a group that was holding
      [*] = ;                  // and gets any other order is RELEASED, and that has to be said aloud -
      [*] = ;                  // otherwise the reader cannot tell a formation on duty from one that walked.
      [*] = ;                  var hagmwas : Integer = ParserGetIntValueByKeyByHandle(hagmp, 'g' + IntToStr(hagid) + '_m');
      [*] = ;                  ParserSetIntValueByKeyByHandle(hagmp, 'g' + IntToStr(hagid) + '_ap', 0);   // a new order cancels a pending hold-on-arrival; re-armed below if this one asks
      [*] = ;                  ParserSetIntValueByKeyByHandle(hagmp, 'g' + IntToStr(hagid) + '_rq', 0);   // and a pending raid retreat; re-armed below by ATTACK ret
      [*] = ;                  var hagm : Integer = 0;
      [*] = ;                  if (hamode = 'move') then hagm := 1;
      [*] = ;                  if (haretreat) then hagm := 2;
      [*] = ;                  if (haengage) then hagm := 3;
      [*] = ;                  if (haface) and (hahold) then hagm := 4;
      [*] = ;                  // MODE 5 = KITES (26.10). Any other order to the group switches the controller off,
      [*] = ;                  // and says so: a group that stopped kiting in silence looks like one that never did.
      [*] = ;                  if (hakite) then hagm := 5;
      [*] = ;                  if (hagmwas = 5) and (hagm <> 5) then
      [*] = ;                  begin
      [*] = ;                     var hakrp : Integer = ParserSelectByKey('br_hkite');
      [*] = ;                     if (hakrp <> 0) then
      [*] = ;                     ParserSetIntValueByKeyByHandle(hakrp, 'g' + IntToStr(hagid) + '_on', 0);
      [*] = ;                     Log('bridge-human: GROUP ' + IntToStr(hagid) + ' kite released by ' + hamw);
      [*] = ;                  end;
      [*] = ;                  if (hamerge) and (hagmwas = 4) then hagm := 4;   // merge: the standing men were not ordered, their hold stands
      [*] = ;                  if (hagmwas = 4) and (hagm <> 4) then
      [*] = ;                  Log('bridge-human: GROUP ' + IntToStr(hagid) + ' hold released by ' +
      [*] = ;                      hamw + ' (mode ' + IntToStr(hagmwas) + ' -> ' + IntToStr(hagm) + ')');
      [*] = ;                  // A FACE that does NOT hold writes the mode only to clear a stale 4: the
      [*] = ;                  // engine has already dropped bstandground (writemove.inc:120), so leaving 4
      [*] = ;                  // in the state would claim men are on duty when they are not. Any other mode
      [*] = ;                  // is written as before; a non-holding FACE of a non-holding group changes
      [*] = ;                  // nothing, because turning is not a mission.
      [*] = ;                  if (not haface) or (hahold) or (hagmwas = 4) then
      [*] = ;                  ParserSetIntValueByKeyByHandle(hagmp, 'g' + IntToStr(hagid) + '_m', hagm);
      [*] = ;               end;
      [*] = ;               // These men are busy now: the next order of this tick skips them.
      [*] = ;               for hak := 0 to gIntegerList.GetCount-1 do
      [*] = ;               gTmpIntList.Add(gIntegerList.Get(hak));
      [*] = ;               // WHICH WAY THE FORMATION LOOKS (5.10, par.98). The engine does TWO things
      [*] = ;               // with dirX,dirZ (units/global.inc/writemove.inc): it builds the group grid
      [*] = ;               // (files along dir, ranks across it, via VectorRotateY(-90)) and gives every
      [*] = ;               // man _unit_OrderMove(..., dirx, dirz) - walk there and turn that way. Damage
      [*] = ;               // does not read it (_misc_DoDamage never touches direction): what it changes
      [*] = ;               // is how the formation stands and which way the ranks look.
      [*] = ;               // It used to be the literal 0,1 in both calls below.
      [*] = ;               //
      [*] = ;               // The vector is from the CENTRE OF THE MEN BEING SENT, averaged over
      [*] = ;               // gIntegerList - not from hatsx of the 'group' branch, which is the centre of
      [*] = ;               // the RECEIVING group and only exists for target=group.
      [*] = ;               var hadsx : Float = 0;
      [*] = ;               var hadsz : Float = 0;
      [*] = ;               var hadk : Integer;
      [*] = ;               for hadk := 0 to gIntegerList.GetCount-1 do
      [*] = ;               begin
      [*] = ;                  hadsx := hadsx + GetGameObjectPositionXByHandle(gIntegerList.Get(hadk));
      [*] = ;                  hadsz := hadsz + GetGameObjectPositionZByHandle(gIntegerList.Get(hadk));
      [*] = ;               end;
      [*] = ;               if (gIntegerList.GetCount > 0) then
      [*] = ;               begin
      [*] = ;                  hadsx := hadsx / gIntegerList.GetCount;
      [*] = ;                  hadsz := hadsz / gIntegerList.GetCount;
      [*] = ;               end;
      [*] = ;               var hadx : Float = 0;
      [*] = ;               var hady : Float = 0;
      [*] = ;               var hadz : Float = 0;
      [*] = ;               var hadwhy : String = 'at the target';
      [*] = ;               // A NAMED CELL BEATS EVERYTHING: keys fx,fy of this order. Presence is the
      [*] = ;               // non-empty STRING, because the integer getter cannot tell a missing key from
      [*] = ;               // a real cell 0,0.
      [*] = ;               if (ParserGetValueByKeyByHandle(hah, hapre + 'fx') <> '') then
      [*] = ;               begin
      [*] = ;                  var hafx : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'fx');
      [*] = ;                  var hafy : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'fy');
      [*] = ;                  if (hafx < 0) then hafx := 0;
      [*] = ;                  if (hafy < 0) then hafy := 0;
      [*] = ;                  if (hafx > hafn-1) then hafx := hafn-1;
      [*] = ;                  if (hafy > hafn-1) then hafy := hafn-1;
      [*] = ;                  hadx := (hafx + 0.5) * hafw / hafn - hafw div 2 - hadsx;
      [*] = ;                  hadz := (hafy + 0.5) * hafh / hafn - hafh div 2 - hadsz;
      [*] = ;                  hadwhy := 'at cell ' + IntToStr(hafx) + ',' + IntToStr(hafy);
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (haretreat) then
      [*] = ;               begin
      [*] = ;                  // RETREAT LOOKS AT THE ENEMY, not where it is going: a column that walks
      [*] = ;                  // home with its back to him is shot in the back. His nearest FIGHTER is
      [*] = ;                  // found here by a scan - the state block has ecells, the command block has
      [*] = ;                  // no access to it, and asking the engine where a heap is is not possible.
      [*] = ;                  var hadbest : Float = 1000000;
      [*] = ;                  var hadfound : Boolean = False;
      [*] = ;                  var hadex : Float = 0;
      [*] = ;                  var hadez : Float = 0;
      [*] = ;                  var hadpl : Integer;
      [*] = ;                  for hadpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;                  if (gPlayer[hadpl].bexists) and (hadpl <> plind) then
      [*] = ;                  if ((gPlayer[plind].enemyPlMask and gPlayer[hadpl].myPlMask) <> 0) then
      [*] = ;                  begin
      [*] = ;                     var hadeph : Integer = GetPlayerHandleByIndex(hadpl);
      [*] = ;                     var haden : Integer = GetPlayerGameObjectsCountByHandle(hadeph);
      [*] = ;                     var hadj : Integer;
      [*] = ;                     for hadj := 0 to haden-1 do
      [*] = ;                     begin
      [*] = ;                        var hadeg : Integer = GetGameObjectHandleByIndex(hadj, hadeph);
      [*] = ;                        var hadep : Pointer = _unit_GetTObj(hadeg);
      [*] = ;                        if (hadep<>nil) then
      [*] = ;                        if (not gObjProp[TObj(hadep).cid][TObj(hadep).id].bbuilding) then
      [*] = ;                        begin
      [*] = ;                           var hadeu : Integer = gObjProp[TObj(hadep).cid][TObj(hadep).id].usage;
      [*] = ;                           if (hadeu <> gc_obj_usage_peasant) and (hadeu <> gc_obj_usage_none) then
      [*] = ;                           begin
      [*] = ;                              var hadd : Float = VectorDistance(
      [*] = ;                                 GetGameObjectPositionXByHandle(hadeg), 0,
      [*] = ;                                 GetGameObjectPositionZByHandle(hadeg), hadsx, 0, hadsz);
      [*] = ;                              if (hadd < hadbest) then
      [*] = ;                              begin
      [*] = ;                                 hadbest := hadd;
      [*] = ;                                 hadex := GetGameObjectPositionXByHandle(hadeg);
      [*] = ;                                 hadez := GetGameObjectPositionZByHandle(hadeg);
      [*] = ;                                 hadfound := True;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hadfound) then
      [*] = ;                  begin
      [*] = ;                     hadx := hadex - hadsx;
      [*] = ;                     hadz := hadez - hadsz;
      [*] = ;                     hadwhy := 'at his nearest fighter';
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     // Nobody of his in sight: stand looking back along the march, which is
      [*] = ;                     // where he was.
      [*] = ;                     hadx := hadsx - hatx;
      [*] = ;                     hadz := hadsz - hatz;
      [*] = ;                     hadwhy := 'back along the march';
      [*] = ;                  end;
      [*] = ;               end
      [*] = ;               else
      [*] = ;               begin
      [*] = ;                  hadx := hatx - hadsx;
      [*] = ;                  hadz := hatz - hadsz;
      [*] = ;               end;
      [*] = ;               // Normalised, as the engine itself does it (terrain/texturemap.inc:441): the
      [*] = ;               // grid multiplies dir by the spacing, so a vector of any other length would
      [*] = ;               // stretch the ranks. Degenerate - the target is where they already stand -
      [*] = ;               // keeps the old 0,1 AND SAYS SO, otherwise it would look like a measured
      [*] = ;               // direction.
      [*] = ;               var hadlen : Float = VectorLength(hadx, hady, hadz);
      [*] = ;               if (hadlen < 1) then
      [*] = ;               begin
      [*] = ;                  hadx := 0;
      [*] = ;                  hadz := 1;
      [*] = ;                  hadwhy := 'degenerate, kept 0,1';
      [*] = ;               end
      [*] = ;               else
      [*] = ;               VectorNormalize(hadx, hady, hadz);
      [*] = ;               // TWO DIGITS BY HAND: this engine has FloatToStr and no FloatToStrF, and
      [*] = ;               // FloatToStr on a normalised vector would print whatever precision it likes -
      [*] = ;               // the mac compares these numbers, so they are composed from hundredths. Both
      [*] = ;               // components are between -1 and 1, so the whole part is 0 or 1.
      [*] = ;               var hadhx : Integer = Round(hadx*100);
      [*] = ;               var hadhz : Integer = Round(hadz*100);
      [*] = ;               var hadsgx : String = '';
      [*] = ;               var hadsgz : String = '';
      [*] = ;               if (hadhx < 0) then hadsgx := '-';
      [*] = ;               if (hadhz < 0) then hadsgz := '-';
      [*] = ;               var hadax : Integer = Round(Abs(hadhx));
      [*] = ;               var hadaz : Integer = Round(Abs(hadhz));
      [*] = ;               var hadfx : String = IntToStr(hadax mod 100);
      [*] = ;               var hadfz : String = IntToStr(hadaz mod 100);
      [*] = ;               if ((hadax mod 100) < 10) then hadfx := '0' + hadfx;
      [*] = ;               if ((hadaz mod 100) < 10) then hadfz := '0' + hadfz;
      [*] = ;               var haddir : String = ' dir=' + hadsgx + IntToStr(hadax div 100) + '.' + hadfx +
      [*] = ;                    ',' + hadsgz + IntToStr(hadaz div 100) + '.' + hadfz + ' (' + hadwhy + ')';
      [*] = ;               if (hakite) then
      [*] = ;               begin
      [*] = ;                  if (hagid > 0) then
      [*] = ;                  begin
      [*] = ;                     // Switched on in a named parser, the way wave_sent and the group rolls live between
      [*] = ;                     // ticks. gap10/step10 are tenths of a tile from python; defaults 1.0 and 4.0 tiles.
      [*] = ;                     var hakp : Integer = ParserSelectByKey('br_hkite');
      [*] = ;                     if (hakp = 0) then
      [*] = ;                     hakp := ParserCreate('br_hkite');
      [*] = ;                     var hakgap : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'gap10');
      [*] = ;                     if (hakgap <= 0) then hakgap := 10;
      [*] = ;                     var hakstep : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'step10');
      [*] = ;                     if (hakstep <= 0) then hakstep := 40;
      [*] = ;                     var hakfar : Integer = ParserGetIntValueByKeyByHandle(hah, hapre + 'far10');
      [*] = ;                     if (hakfar <= 0) then hakfar := 300;
      [*] = ;                     ParserSetIntValueByKeyByHandle(hakp, 'g' + IntToStr(hagid) + '_on', 1);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hakp, 'g' + IntToStr(hagid) + '_st', 0);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hakp, 'g' + IntToStr(hagid) + '_gap10', hakgap);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hakp, 'g' + IntToStr(hagid) + '_step10', hakstep);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hakp, 'g' + IntToStr(hagid) + '_far10', hakfar);
      [*] = ;                     // Hold where they stand right away, facing the named cell: the controller takes over
      [*] = ;                     // on its next second. Same two calls and same order as FACE hold (par.102).
      [*] = ;                     _player_SetGroupPosition(haph, hagr, -1, hadsx, hadsz, hadsx, hadsz, hadx, hadz,
      [*] = ;                          False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                     _misc_SetUnitsListUnitState(gIntegerList, True, False, True, False);
      [*] = ;                     Log('bridge-human: KITE group ' + IntToStr(hagid) + ' on: ' + IntToStr(gIntegerList.GetCount) +
      [*] = ;                         ' shooters at ' + FloatToStr(hadsx) + ',' + FloatToStr(hadsz) + haddir +
      [*] = ;                         ' gap10=' + IntToStr(hakgap) + ' step10=' + IntToStr(hakstep) + ' far10=' + IntToStr(hakfar));
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') +
      [*] = ;                          ' | KITE: needs a group number (group N), nobody kites');
      [*] = ;                     Log('bridge-human: KITE skipped - needs a group number');
      [*] = ;                  end;
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (haface) then
      [*] = ;               begin
      [*] = ;                  // THE SAME CALL, only the point is where they ALREADY stand: men walk a

      [*] = ;                  // step inside their own formation and turn. rebuild True on purpose - that
      [*] = ;                  // is what re-lays the grid along the new direction.
      [*] = ;                  _player_SetGroupPosition(haph, hagr, -1, hadsx, hadsz, hadsx, hadsz, hadx, hadz,
      [*] = ;                       False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                  // HOLD AFTER THE TURN, and in that order: SetGroupPosition goes through
      [*] = ;                  // WriteMove, which clears bstandground (writemove.inc:120) - setting the
      [*] = ;                  // flag first would lose it. The engine procedure is the one the player's
      [*] = ;                  // own button uses (lib/misc.script:2208): it sets BOTH TSquad.fStandGround
      [*] = ;                  // and TObj.bstandground, and a squad half-held would behave by the squad
      [*] = ;                  // flag (unit.script:8152).
      [*] = ;                  var hahw : String = '';
      [*] = ;                  if (hahold) then
      [*] = ;                  begin
      [*] = ;                     _misc_SetUnitsListUnitState(gIntegerList, True, False, True, False);
      [*] = ;                     hahw := ' hold';
      [*] = ;                  end;
      [*] = ;                  Log('bridge-human: FACE ' + IntToStr(gIntegerList.GetCount) + ' in place at ' +
      [*] = ;                      FloatToStr(hadsx) + ',' + FloatToStr(hadsz) + haddir + hahw);
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (hamode = 'move') or (haretreat) then
      [*] = ;               begin
      [*] = ;                  // No _unit_ListSetSearchEnemy here on purpose: that is what turns a
      [*] = ;                  // walk into a hunt. Mode default is how the game itself moves a
      [*] = ;                  // group - player.script:2503.
      [*] = ;                  _player_SetGroupPosition(haph, hagr, -1, hatx, hatz, hatx, hatz, hadx, hadz,
      [*] = ;                       False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                  Log('bridge-human: MOVE ' + IntToStr(gIntegerList.GetCount) + ' target=' + hatrg +
      [*] = ;                      ' at ' + FloatToStr(hatx) + ',' + FloatToStr(hatz) + haddir);
      [*] = ;                  if (haarrive) and (hagid > 0) and (hamode = 'move') then
      [*] = ;                  begin
      [*] = ;                     var hagap : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;                     if (hagap <> 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetIntValueByKeyByHandle(hagap, 'g' + IntToStr(hagid) + '_ap', 1);
      [*] = ;                        ParserSetFloatValueByKeyByHandle(hagap, 'g' + IntToStr(hagid) + '_ax', hatx);
      [*] = ;                        ParserSetFloatValueByKeyByHandle(hagap, 'g' + IntToStr(hagid) + '_az', hatz);
      [*] = ;                        ParserSetFloatValueByKeyByHandle(hagap, 'g' + IntToStr(hagid) + '_at', GetGameTime);
      [*] = ;                        var hagsl : Integer = -1;
      [*] = ;                        var hagk4 : Integer;
      [*] = ;                        for hagk4 := 0 to 7 do
      [*] = ;                        if (ParserGetIntValueByKeyByHandle(hagap, 'hp' + IntToStr(hagk4)) = hagid) then hagsl := hagk4;
      [*] = ;                        if (hagsl < 0) then
      [*] = ;                        for hagk4 := 0 to 7 do
      [*] = ;                        if (hagsl < 0) and (ParserGetIntValueByKeyByHandle(hagap, 'hp' + IntToStr(hagk4)) = 0) then hagsl := hagk4;
      [*] = ;                        if (hagsl >= 0) then
      [*] = ;                        ParserSetIntValueByKeyByHandle(hagap, 'hp' + IntToStr(hagsl), hagid);
      [*] = ;                        Log('bridge-human: GROUP ' + IntToStr(hagid) + ' hold on arrival armed at ' + FloatToStr(hatx) + ',' + FloatToStr(hatz));
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (haretreat) then
      [*] = ;                  Log('bridge-human: RETREAT ' + IntToStr(gIntegerList.GetCount) +
      [*] = ;                      ' far soldiers walk home [field>' + IntToStr(hafr) + ' cell from ' + IntToStr(hafbx) + ',' + IntToStr(hafby) + ']');
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (_unit_ListSetSearchEnemy(haph, gIntegerList, True, True)) then
      [*] = ;               begin
      [*] = ;                  if (haall) or (hadefn) then
      [*] = ;                  begin
      [*] = ;                     // ALL (and the defensive ATTACK, item 2): the holding men taken above are released before the move (same call as FACE hold, state False)
      [*] = ;                     _misc_SetUnitsListUnitState(gIntegerList, True, False, False, False);
      [*] = ;                  end;
      [*] = ;                  _player_SetGroupPosition(haph, hagr, -1, hatx, hatz, hatx, hatz, hadx, hadz,
      [*] = ;                       False, False, True, True, gc_obj_order_move_mode_attack);
      [*] = ;                  Log('bridge-human: ATTACK ' + IntToStr(gIntegerList.GetCount) + ' target=' + hatrg +
      [*] = ;                      ' at ' + FloatToStr(hatx) + ',' + FloatToStr(hatz) + haddir);
      [*] = ;                  // AND THE WALL IS ATTACKED AS AN OBJECT (1.11). SetGroupPosition above is a MOVE:
      [*] = ;                  // with a sealed palisade there is no path, the group stands and the wall is never
      [*] = ;                  // touched. The list order below is the same shape the bridge already uses for mines
      [*] = ;                  // (_player_OrderUnitsToGoInside at the top of this file): clear gPtrList, pass it as
      [*] = ;                  // squads. Without it target=wall would only walk the men up to the fence.
      [*] = ;                  if (hawallh > 0) then
      [*] = ;                  begin
      [*] = ;                     gPtrList.Clear;
      [*] = ;                     _player_OrderUnitsToAttack(plind, hawallh, gIntegerList, gPtrList, True, False);
      [*] = ;                     Log('bridge-human: ATTACK wall object ' + IntToStr(hawallh) + ' by ' +
      [*] = ;                         IntToStr(gIntegerList.GetCount) + ' men at ' + FloatToStr(hatx) + ',' + FloatToStr(hatz));
      [*] = ;                  end;
      [*] = ;                  // Wave size goes into a NAMED PARSER, not into a group. 14.09 the
      [*] = ;                  // 'one group per wave' fix renamed the groups to coss3_wave_0..7,
      [*] = ;                  // and block_hstate went on counting the old coss3_bridge_wave -
      [*] = ;                  // empty forever. wave_sent was zero in EVERY run since, and the
      [*] = ;                  // model read 'no waves at all' right after sending one.
      [*] = ;                  // A named parser lives between ticks and knows nothing of groups.
      [*] = ;                  if (haengage) then
      [*] = ;                  Log('bridge-human: ENGAGE ' + IntToStr(gIntegerList.GetCount) +
      [*] = ;                      ' far soldiers turn to fight [field>' + IntToStr(hafr) + ' cell from ' + IntToStr(hafbx) + ',' + IntToStr(hafby) + ']');
      [*] = ;                  // ENGAGE is not a new wave: wave_sent stays as it was.
      [*] = ;                  if (not haengage) then
      [*] = ;                  begin
      [*] = ;                     var hawp : Integer = ParserSelectByKey('br_hwave');
      [*] = ;                     if (hawp = 0) then
      [*] = ;                     hawp := ParserCreate('br_hwave');
      [*] = ;                     ParserSetIntValueByKeyByHandle(hawp, 'sent', gIntegerList.GetCount);
      [*] = ;                  end;
      [*] = ;                  if (haret > 0) and (hagid > 0) and (not haengage) then
      [*] = ;                  begin
      [*] = ;                     var harap : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;                     if (harap = 0) then
      [*] = ;                     harap := ParserCreate('br_hgrp');
      [*] = ;                     var harsl : Integer = -1;
      [*] = ;                     var hark : Integer;
      [*] = ;                     for hark := 0 to 7 do
      [*] = ;                     if (ParserGetIntValueByKeyByHandle(harap, 'rp' + IntToStr(hark)) = hagid) then harsl := hark;
      [*] = ;                     if (harsl < 0) then
      [*] = ;                     for hark := 0 to 7 do
      [*] = ;                     if (harsl < 0) and (ParserGetIntValueByKeyByHandle(harap, 'rp' + IntToStr(hark)) = 0) then harsl := hark;
      [*] = ;                     if (harsl >= 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetIntValueByKeyByHandle(harap, 'rp' + IntToStr(harsl), hagid);
      [*] = ;                        ParserSetIntValueByKeyByHandle(harap, 'g' + IntToStr(hagid) + '_rq', 1);
      [*] = ;                        ParserSetFloatValueByKeyByHandle(harap, 'g' + IntToStr(hagid) + '_rt', GetGameTime + haret);
      [*] = ;                        ParserSetFloatValueByKeyByHandle(harap, 'g' + IntToStr(hagid) + '_rx', hax);
      [*] = ;                        ParserSetFloatValueByKeyByHandle(harap, 'g' + IntToStr(hagid) + '_rz', haz);
      [*] = ;                        Log('bridge-human: GROUP ' + IntToStr(hagid) + ' retreat armed: home in ' + IntToStr(haret) + ' s');
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     Log('bridge-human: GROUP ' + IntToStr(hagid) + ' retreat NOT armed: all 8 retreat slots busy');
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               // SQUAD BY GROUP NUMBER (29.10 evening, mac, block task No3). A numbered order goes through WriteMove with
      [*] = ;               // squad -1: every man walks on his own and the formation he stood in is left behind (writemove.inc:35 rebuilds
      [*] = ;               // the grid only for squad >= 0). After the group call above, every squad that has a man in this list gets THE
      [*] = ;               // SAME order as a squad (_player_SetSquadPosition - grid rebuilt, bonus kept, the later order wins the tick):
      [*] = ;               // attack and engage with the hunt on, move and retreat without it, FACE in place at the squad's own centre with
      [*] = ;               // the hold set after the move, as FACE does for men. Kite is left alone: it is a controller for shooters.
      [*] = ;               if (hagid > 0) and (not hakite) then
      [*] = ;               begin
      [*] = ;                  var hgsn : Integer = 0;
      [*] = ;                  var hgsm : Integer = 0;
      [*] = ;                  var hgsi : Integer;
      [*] = ;                  for hgsi := 0 to gPlayer[plind].squads.GetCount-1 do
      [*] = ;                  begin
      [*] = ;                     var hgsp : Pointer = gPlayer[plind].squads.Get(hgsi);
      [*] = ;                     if (hgsp<>nil) then
      [*] = ;                     if (TSquad(hgsp).GetCount > 0) then
      [*] = ;                     begin
      [*] = ;                        var hgsin : Boolean = False;
      [*] = ;                        var hgsj : Integer;
      [*] = ;                        for hgsj := 0 to TSquad(hgsp).GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hgsh : Integer = TSquad(hgsp).Get(hgsj);
      [*] = ;                           var hgsk : Integer;
      [*] = ;                           for hgsk := 0 to gIntegerList.GetCount-1 do
      [*] = ;                           begin
      [*] = ;                              if (gIntegerList.Get(hgsk) = hgsh) then hgsin := True;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hgsin) then
      [*] = ;                        begin
      [*] = ;                           var hgsx : Float = 0;
      [*] = ;                           var hgsz : Float = 0;
      [*] = ;                           _squad_GetCentralPosition(hgsp, hgsx, hgsz);
      [*] = ;                           var hgtx : Float = hatx;
      [*] = ;                           var hgtz : Float = hatz;
      [*] = ;                           var hgmode : Integer = gc_obj_order_move_mode_attack;
      [*] = ;                           var hghunt : Boolean = True;
      [*] = ;                           if (haface) then
      [*] = ;                           begin
      [*] = ;                              hgtx := hgsx;
      [*] = ;                              hgtz := hgsz;
      [*] = ;                              hgmode := gc_obj_order_move_mode_default;
      [*] = ;                              hghunt := False;
      [*] = ;                           end;
      [*] = ;                           if (hamode = 'move') or (haretreat) then
      [*] = ;                           begin
      [*] = ;                              hgmode := gc_obj_order_move_mode_default;
      [*] = ;                              hghunt := False;
      [*] = ;                           end;
      [*] = ;                           TSquad(hgsp).fSearchVictim := hghunt;
      [*] = ;                           TSquad(hgsp).fStandGround := False;
      [*] = ;                           TSquad(hgsp).fHoldMode := False;
      [*] = ;                           TSquad(hgsp).fHoldModeProgress := 0;
      [*] = ;                           for hgsj := 0 to TSquad(hgsp).GetCount-1 do
      [*] = ;                           begin
      [*] = ;                              var hgsh2 : Integer = TSquad(hgsp).Get(hgsj);
      [*] = ;                              var hgsu : Pointer = _unit_GetTObj(hgsh2);
      [*] = ;                              if (hgsu<>nil) then
      [*] = ;                              begin
      [*] = ;                                 TObj(hgsu).bsearchenemy := hghunt;
      [*] = ;                                 TObj(hgsu).bstandground := False;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                           _player_SetSquadPosition(haph, hgsi, hgtx, hgtz, hadx, hadz, False, True, hgmode, False);
      [*] = ;                           if (haface) and (hahold) then
      [*] = ;                           begin
      [*] = ;                              TSquad(hgsp).fStandGround := True;
      [*] = ;                              for hgsj := 0 to TSquad(hgsp).GetCount-1 do
      [*] = ;                              begin
      [*] = ;                                 var hgsh3 : Integer = TSquad(hgsp).Get(hgsj);
      [*] = ;                                 var hgsu3 : Pointer = _unit_GetTObj(hgsh3);
      [*] = ;                                 if (hgsu3<>nil) then
      [*] = ;                                 TObj(hgsu3).bstandground := True;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                           hgsn := hgsn + 1;
      [*] = ;                           hgsm := hgsm + TSquad(hgsp).GetCount;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hgsn > 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'GROUP ' + IntToStr(hagid) +
      [*] = ;                          ' ' + hamw + ': ' + IntToStr(hgsn) + ' squads (' + IntToStr(hgsm) + ' men) re-ordered as squads, formation kept');
      [*] = ;                     Log('bridge-human: GROUP ' + IntToStr(hagid) + ' ' + hamw + ': ' + IntToStr(hgsn) + ' squads, ' + IntToStr(hgsm) + ' men ordered as squads');
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end
      [*] = ;            else
      [*] = ;            Log('bridge-human: ATTACK skipped - soldiers ' + IntToStr(gIntegerList.GetCount) +
      [*] = ;                ', target found ' + BoolToStr(hafound) + ' [field>' + IntToStr(hafr) + ' cell from ' + IntToStr(hafbx) + ',' + IntToStr(hafby) + ']');
      [*] = ;            // ALL: every squad of ours goes AS A SQUAD to the same target, with its hold released. Stands apart
      [*] = ;            // from the wave above on purpose: when the whole army is in squads the wave list is empty, and
      [*] = ;            // the squads must still go. Hold is released exactly as lib/unit.script _unit_SetSquadsStandGround does.
      [*] = ;            if (haall) and (hafound) and (not haretreat) and (not haface) and (not hakite) and (hamode <> 'move') then
      [*] = ;            begin
      [*] = ;               var hasqi : Integer;
      [*] = ;               for hasqi := 0 to gPlayer[plind].squads.GetCount-1 do
      [*] = ;               begin
      [*] = ;                  var hasqp : Pointer = gPlayer[plind].squads.Get(hasqi);
      [*] = ;                  if (hasqp<>nil) then
      [*] = ;                  if (TSquad(hasqp).GetCount > 0) then
      [*] = ;                  begin
      [*] = ;                     var hasqx : Float = 0;
      [*] = ;                     var hasqz : Float = 0;
      [*] = ;                     _squad_GetCentralPosition(hasqp, hasqx, hasqz);
      [*] = ;                     var hasdx : Float = hatx - hasqx;
      [*] = ;                     var hasdy : Float = 0;
      [*] = ;                     var hasdz : Float = hatz - hasqz;
      [*] = ;                     VectorNormalize(hasdx, hasdy, hasdz);
      [*] = ;                     TSquad(hasqp).fStandGround := False;
      [*] = ;                     TSquad(hasqp).fHoldMode := False;
      [*] = ;                     TSquad(hasqp).fHoldModeProgress := 0;
      [*] = ;                     var hasqj : Integer;
      [*] = ;                     for hasqj := 0 to TSquad(hasqp).GetCount-1 do
      [*] = ;                     begin
      [*] = ;                        var hasqh : Integer = TSquad(hasqp).Get(hasqj);
      [*] = ;                        var hasqu : Pointer = _unit_GetTObj(hasqh);
      [*] = ;                        if (hasqu<>nil) then
      [*] = ;                        begin
      [*] = ;                           TObj(hasqu).bstandground := False;
      [*] = ;                           TObj(hasqu).bsearchenemy := True;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     // HUNT (29.10 evening, mac, block task No3). The wave above gets _unit_ListSetSearchEnemy; the squad got
      [*] = ;                     // nothing and walked to the target as a parade (state_held_vs_ai x2: four exits of 125 men, his peasants
      [*] = ;                     // 11 -> 10). Same two fields the lib writes in _unit_SetSquadsSearchEnemy (unit.script:10583, :10589),
      [*] = ;                     // set here because that call wants a list of squad indices and both temp lists are busy in this branch.
      [*] = ;                     TSquad(hasqp).fSearchVictim := True;
      [*] = ;                     _player_SetSquadPosition(haph, hasqi, hatx, hatz, hasdx, hasdz, False, True, gc_obj_order_move_mode_attack, False);
      [*] = ;                     hasqn := hasqn + 1;
      [*] = ;                     hasqm := hasqm + TSquad(hasqp).GetCount;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               ParserSetValueByKeyByHandle(hfl, 'why', ParserGetValueByKeyByHandle(hfl, 'why') + ' | ' + 'ATTACK all: ' +
      [*] = ;                    IntToStr(hasqn) + ' squads (' + IntToStr(hasqm) + ' men) sent as squads to ' + hatrg + ', hold released');
      [*] = ;               Log('bridge-human: ATTACK all: ' + IntToStr(hasqn) + ' squads, ' + IntToStr(hasqm) + ' men sent as squads to ' + hatrg + ', search enemy on');
      [*] = ;            end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // --- KITE CONTROLLER (26.10, question of the player: 'can a musketeer shoot, step back,
      [*] = ;      // shoot again until the pike is dead?'). Numbers from unit.script: musketeer rmin 7.5 tiles,
      [*] = ;      // rmax 15, pause 3.75 s, pikeman reach 1.9, ALL infantry at gc_obj_speed_default - equal speed.
      [*] = ;      // So one shooter cannot out-walk one pike; what a player does is a VOLLEY from hold, a step
      [*] = ;      // back when the pike gets near the minimum range, another volley - in a group, with the base
      [*] = ;      // behind. Every game second, for each group a KITE order switched on:
      [*] = ;      //   melee of his nearer than rmin+gap  -> step back `step` tiles, away from him and bent towards
      [*] = ;      //                                          our hall; not beyond `far` tiles from the hall (then hold);
      [*] = ;      //   anybody of his within rmax+gap     -> hold where we stand: a HOLDING shooter searches victims
      [*] = ;      //                                          to his full radius (unit.script:7259), an idle one only to
      [*] = ;      //                                          minattackradius+0.375 - idle shooters do NOT fire at 15;
      [*] = ;      //   nobody in range                    -> hold and wait.
      [*] = ;      // Any other order to the group, or nobody alive, switches it off (mode 5 in `groups`).
      [*] = ;      // Zero cost until the first KITE order: the parser does not exist before it.
      [*] = ;      // === TOPUP (29.10, mac, block task No1): idle men to the resource below its target, once a second ===
      [*] = ;      // Targets come from the last command file (br_hbal, see TOPUP STORE). Only IDLE men are moved - a man already
      [*] = ;      // gathering is never touched, so this cannot walk anybody in circles. Food is searched around the MILL, wood and
      [*] = ;      // stone around the town hall, exactly as the BALANCE command does. Skipped for a second after a command file,
      [*] = ;      // so python's own orders of the tick apply first.
      [*] = ;      var htp : Integer = ParserSelectByKey('br_hbal');
      [*] = ;      if (htp <> 0) then
      [*] = ;      if (ParserGetIntValueByKeyByHandle(htp, 'set' + IntToStr(plind)) = 1) then
      [*] = ;      begin
      [*] = ;         var htnow : Float = GetGameTime;
      [*] = ;         var htlast : Float = ParserGetFloatValueByKeyByHandle(htp, 'at' + IntToStr(plind));
      [*] = ;         var htcmd : Float = ParserGetFloatValueByKeyByHandle(htp, 'cmd' + IntToStr(plind));
      [*] = ;         if (htnow < htcmd) then
      [*] = ;         begin
      [*] = ;            ParserSetIntValueByKeyByHandle(htp, 'set' + IntToStr(plind), 0);
      [*] = ;         end
      [*] = ;         else
      [*] = ;         if ((htnow - htlast >= 1.0) or (htnow < htlast)) and (htnow - htcmd >= 1.0) then
      [*] = ;         begin
      [*] = ;            ParserSetFloatValueByKeyByHandle(htp, 'at' + IntToStr(plind), htnow);
      [*] = ;            var httf : Integer = ParserGetIntValueByKeyByHandle(htp, 'tf' + IntToStr(plind));
      [*] = ;            var httw : Integer = ParserGetIntValueByKeyByHandle(htp, 'tw' + IntToStr(plind));
      [*] = ;            var htts : Integer = ParserGetIntValueByKeyByHandle(htp, 'ts' + IntToStr(plind));
      [*] = ;            if (ParserGetValueByKeyByHandle(htp, 'tf' + IntToStr(plind)) = '') then
      [*] = ;            begin
      [*] = ;               httf := -1;
      [*] = ;            end;
      [*] = ;            if (ParserGetValueByKeyByHandle(htp, 'tw' + IntToStr(plind)) = '') then
      [*] = ;            begin
      [*] = ;               httw := -1;
      [*] = ;            end;
      [*] = ;            if (ParserGetValueByKeyByHandle(htp, 'ts' + IntToStr(plind)) = '') then
      [*] = ;            begin
      [*] = ;               htts := -1;
      [*] = ;            end;
      [*] = ;            var htph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var htoc : Integer = GetPlayerGameObjectsCountByHandle(htph);
      [*] = ;            var htf : Integer = 0;
      [*] = ;            var htw : Integer = 0;
      [*] = ;            var hts : Integer = 0;
      [*] = ;            var hthx : Float = 0;
      [*] = ;            var hthz : Float = 0;
      [*] = ;            var hthall : Boolean = False;
      [*] = ;            var htmx : Float = 0;
      [*] = ;            var htmz : Float = 0;
      [*] = ;            var htmill : Boolean = False;
      [*] = ;            var htk : Integer;
      [*] = ;            gTmpIntList.Clear;
      [*] = ;            for htk := 0 to htoc-1 do
      [*] = ;            begin
      [*] = ;               var htgo : Integer = GetGameObjectHandleByIndex(htk, htph);
      [*] = ;               var htpo : Pointer = _unit_GetTObj(htgo);
      [*] = ;               if (htpo<>nil) then
      [*] = ;               // TOPUP: dead peasants are not idle hands (31.10)
      [*] = ;               if (not TObj(htpo).bdead) then
      [*] = ;               begin
      [*] = ;                  var htrole : Integer = gObjProp[TObj(htpo).cid][TObj(htpo).id].airole;
      [*] = ;                  if (htrole = gc_ai_unit_center) and (not hthall) then
      [*] = ;                  begin
      [*] = ;                     hthall := True;
      [*] = ;                     hthx := GetGameObjectPositionXByHandle(htgo);
      [*] = ;                     hthz := GetGameObjectPositionZByHandle(htgo);
      [*] = ;                  end;
      [*] = ;                  if (htrole = gc_ai_unit_mill) and (not htmill) then
      [*] = ;                  if (TObj(htpo).bbuilt) then
      [*] = ;                  begin
      [*] = ;                     htmill := True;
      [*] = ;                     htmx := GetGameObjectPositionXByHandle(htgo);
      [*] = ;                     htmz := GetGameObjectPositionZByHandle(htgo);
      [*] = ;                  end;
      [*] = ;                  if (gObjProp[TObj(htpo).cid][TObj(htpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                  if (TObj(htpo).insideofuid = 0) then
      [*] = ;                  begin
      [*] = ;                     var htot : Integer = TObj(htpo).orders[0].itype;
      [*] = ;                     if (htot = gc_obj_order_type_gainres) then
      [*] = ;                     begin
      [*] = ;                        var htrp : Pointer = _res_GetTRes(TObj(htpo).orders[0].info.trg);
      [*] = ;                        if (htrp<>nil) then
      [*] = ;                        begin
      [*] = ;                           if (TRes(htrp).itype = gc_resource_type_food) then htf := htf + 1;
      [*] = ;                           if (TRes(htrp).itype = gc_resource_type_wood) then htw := htw + 1;
      [*] = ;                           if (TRes(htrp).itype = gc_resource_type_stone) then hts := hts + 1;
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (htot = gc_obj_order_type_none) then
      [*] = ;                     if (not TObj(htpo).bstandground) then
      [*] = ;                     gTmpIntList.Add(htgo);
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (gTmpIntList.GetCount > 0) and (hthall) then
      [*] = ;            begin
      [*] = ;               // SINK (29.10, mac, No1b, after balance_topup_vs_ai: idle 3+ in 22-31 % of ticks while every target
      [*] = ;               // was met - python let 10 out of the gold mine and its own 50 s transfer term refused to seat them).
      [*] = ;               // Passes 3..5: whoever is still idle after the targets goes to wood, else food (mill), else stone.
      [*] = ;               // Nobody stands. BALANCE and MINE take these men back as donors (above target), see No1b there.
      [*] = ;               var htr : Integer;
      [*] = ;               // SINK ORDER (29.10 evening, mac, after balance_sink_vs_ai): the sink parked all 45 surplus men on wood
      [*] = ;               // while wood lay at 900 and stone at 80, and the gold mine waited for stone from 2:07 to 3:26 (base 3:27,
      [*] = ;               // here 4:07 / 4:38). The surplus now goes to the SCARCEST of wood / stone / food by the treasury (food only
      [*] = ;               // with a mill), the next pass to the next one. Ranks = how many sink resources are scarcer; ties keep wood
      [*] = ;               // first. The treasury is read as the state block reads it (not gPlayer[].res[]).
      [*] = ;               var htsw : Integer = 0;
      [*] = ;               var htss : Integer = 0;
      [*] = ;               var htsf : Integer = 0;
      [*] = ;               htsw := not gPlayer[plind].res[gc_resource_type_wood];
      [*] = ;               htss := not gPlayer[plind].res[gc_resource_type_stone];
      [*] = ;               htsf := not gPlayer[plind].res[gc_resource_type_food];
      [*] = ;               var htrw : Integer = 0;
      [*] = ;               var htrs : Integer = 0;
      [*] = ;               var htrf : Integer = 3;
      [*] = ;               if (htss < htsw) then htrw := htrw + 1;
      [*] = ;               if (htsw <= htss) then htrs := htrs + 1;
      [*] = ;               if (htmill) then
      [*] = ;               begin
      [*] = ;                  htrf := 0;
      [*] = ;                  if (htsf < htsw) then htrw := htrw + 1;
      [*] = ;                  if (htsf < htss) then htrs := htrs + 1;
      [*] = ;                  if (htsw <= htsf) then htrf := htrf + 1;
      [*] = ;                  if (htss <= htsf) then htrf := htrf + 1;
      [*] = ;               end;
      [*] = ;               for htr := 0 to 5 do
      [*] = ;               if (gTmpIntList.GetCount > 0) then
      [*] = ;               begin
      [*] = ;                  var htres : Integer = -1;
      [*] = ;                  var htneed : Integer = 0;
      [*] = ;                  var httarget : Integer = 0;
      [*] = ;                  var hthad : Integer = 0;
      [*] = ;                  var htri : Integer = -1;   // resource in GATHER numbering for the log: 0 food, 1 wood, 2 stone
      [*] = ;                  var htfx : Float = hthx;
      [*] = ;                  var htfz : Float = hthz;
      [*] = ;                  if (htr = 0) and (httf >= 0) and (htmill) then
      [*] = ;                  begin
      [*] = ;                     htres := gc_resource_type_food;
      [*] = ;                     httarget := httf;
      [*] = ;                     hthad := htf;
      [*] = ;                     htfx := htmx;
      [*] = ;                     htfz := htmz;
      [*] = ;                  end;
      [*] = ;                  if (htr = 1) and (httw >= 0) then
      [*] = ;                  begin
      [*] = ;                     htres := gc_resource_type_wood;
      [*] = ;                     httarget := httw;
      [*] = ;                     hthad := htw;
      [*] = ;                  end;
      [*] = ;                  if (htr = 2) and (htts >= 0) then
      [*] = ;                  begin
      [*] = ;                     htres := gc_resource_type_stone;
      [*] = ;                     httarget := htts;
      [*] = ;                     hthad := hts;
      [*] = ;                  end;
      [*] = ;                  if (htr = 3 + htrw) then
      [*] = ;                  begin
      [*] = ;                     htres := gc_resource_type_wood;
      [*] = ;                     httarget := -1;
      [*] = ;                     hthad := htw;
      [*] = ;                     htri := 1;
      [*] = ;                  end;
      [*] = ;                  if (htr = 3 + htrf) and (htmill) then
      [*] = ;                  begin
      [*] = ;                     htres := gc_resource_type_food;
      [*] = ;                     httarget := -1;
      [*] = ;                     hthad := htf;
      [*] = ;                     htfx := htmx;
      [*] = ;                     htfz := htmz;
      [*] = ;                     htri := 0;
      [*] = ;                  end;
      [*] = ;                  if (htr = 3 + htrs) then
      [*] = ;                  begin
      [*] = ;                     htres := gc_resource_type_stone;
      [*] = ;                     httarget := -1;
      [*] = ;                     hthad := hts;
      [*] = ;                     htri := 2;
      [*] = ;                  end;
      [*] = ;                  htneed := httarget - hthad;
      [*] = ;                  if (htr >= 3) then htneed := gTmpIntList.GetCount;
      [*] = ;                  if (htres >= 0) and (htneed > 0) then
      [*] = ;                  begin
      [*] = ;                     if (htneed > gTmpIntList.GetCount) then htneed := gTmpIntList.GetCount;
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     _misc_MakeListEnvironmentInRadius(htfx, htfz, 40, True, True, True, True, False, gIntegerList);
      [*] = ;                     var httrg : Integer = 0;
      [*] = ;                     var htbest : Float = 1000000;
      [*] = ;                     var htj : Integer;
      [*] = ;                     for htj := 0 to gIntegerList.GetCount-1 do
      [*] = ;                     begin
      [*] = ;                        var hth : Integer = gIntegerList.Get(htj);
      [*] = ;                        var htrp2 : Pointer = _res_GetTRes(hth);
      [*] = ;                        if (htrp2<>nil) then
      [*] = ;                        if (TRes(htrp2).brised) and (TRes(htrp2).itype = htres) then
      [*] = ;                        begin
      [*] = ;                           var htd : Float = VectorDistance(GetGameObjectPositionXByHandle(hth), 0,
      [*] = ;                                GetGameObjectPositionZByHandle(hth), hthx, 0, hthz);
      [*] = ;                           if (htd < htbest) then
      [*] = ;                           begin
      [*] = ;                              htbest := htd;
      [*] = ;                              httrg := hth;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (httrg <> 0) then
      [*] = ;                     begin
      [*] = ;                        var htpx : Float = GetGameObjectPositionXByHandle(httrg);
      [*] = ;                        var htpz : Float = GetGameObjectPositionZByHandle(httrg);
      [*] = ;                        var htsent : Integer = 0;
      [*] = ;                        while (htsent < htneed) and (gTmpIntList.GetCount > 0) do
      [*] = ;                        begin
      [*] = ;                           var htgo2 : Integer = gTmpIntList.Get(gTmpIntList.GetCount-1);
      [*] = ;                           gTmpIntList.Delete(gTmpIntList.GetCount-1);
      [*] = ;                           _unit_OrderGainResource(htgo2, httrg, htpx, htpz);
      [*] = ;                           htsent := htsent + 1;
      [*] = ;                        end;
      [*] = ;                        if (htr < 3) then
      [*] = ;                        begin
      [*] = ;                           Log('bridge-human: TOPUP res' + IntToStr(htr) + ' +' + IntToStr(htsent) + ' idle (had ' +
      [*] = ;                               IntToStr(hthad) + ', target ' + IntToStr(httarget) + ')');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           Log('bridge-human: TOPUP sink res' + IntToStr(htri) + ' +' + IntToStr(htsent) + ' idle (had ' +
      [*] = ;                               IntToStr(hthad) + ', no target below; scarcest first, treasury food/wood/stone ' +
      [*] = ;                               IntToStr(htsf) + '/' + IntToStr(htsw) + '/' + IntToStr(htss) + ')');
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      var hkp : Integer = ParserSelectByKey('br_hkite');
      [*] = ;      if (hkp <> 0) then
      [*] = ;      begin
      [*] = ;         var hknow : Float = GetGameTime;
      [*] = ;         var hklast : Float = ParserGetFloatValueByKeyByHandle(hkp, 'at' + IntToStr(plind));
      [*] = ;         if (hknow - hklast >= 1.0) or (hknow < hklast) then
      [*] = ;         begin
      [*] = ;            ParserSetFloatValueByKeyByHandle(hkp, 'at' + IntToStr(plind), hknow);
      [*] = ;            var hkph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var hkgp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;            // Every number that ACCUMULATES is declared HERE and reset by assignment in the loop:
      [*] = ;            // a scalar declared in a nested begin does not accumulate (17.09, six army counters).
      [*] = ;            var hkn : Integer = 0;
      [*] = ;            var hksx : Float = 0;
      [*] = ;            var hksz : Float = 0;
      [*] = ;            var hkbest : Float = 1000000;
      [*] = ;            var hkany : Float = 1000000;
      [*] = ;            var hkex : Float = 0;
      [*] = ;            var hkez : Float = 0;
      [*] = ;            var hkrmin : Float = 0;
      [*] = ;            var hkrmax : Float = 0;
      [*] = ;            var hkerm : Float = 0;
      [*] = ;            var hked : Float = 0;
      [*] = ;            var hkgid, hkk, hkpl, hkj, hkw : Integer;
      [*] = ;            var hkhx : Float = 0;
      [*] = ;            var hkhz : Float = 0;
      [*] = ;            var hkhall : Boolean = False;
      [*] = ;            var hkon : Integer = 0;
      [*] = ;            for hkgid := 1 to 99 do
      [*] = ;            if (ParserGetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_on') = 1) then
      [*] = ;            hkon := hkon + 1;
      [*] = ;            if (hkon > 0) and (hkgp <> 0) then
      [*] = ;            begin
      [*] = ;               // Our hall: the anchor the step back bends towards and the edge it stops at.
      [*] = ;               var hkoc : Integer = GetPlayerGameObjectsCountByHandle(hkph);
      [*] = ;               for hkk := 0 to hkoc-1 do
      [*] = ;               if (not hkhall) then
      [*] = ;               begin
      [*] = ;                  var hkgo : Integer = GetGameObjectHandleByIndex(hkk, hkph);
      [*] = ;                  var hkpo : Pointer = _unit_GetTObj(hkgo);
      [*] = ;                  if (hkpo<>nil) then
      [*] = ;                  if (gObjProp[TObj(hkpo).cid][TObj(hkpo).id].airole = gc_ai_unit_center) then
      [*] = ;                  begin
      [*] = ;                     hkhx := GetGameObjectPositionXByHandle(hkgo);
      [*] = ;                     hkhz := GetGameObjectPositionZByHandle(hkgo);
      [*] = ;                     hkhall := True;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               for hkgid := 1 to 99 do
      [*] = ;               if (ParserGetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_on') = 1) then
      [*] = ;               begin
      [*] = ;                  hkn := 0;
      [*] = ;                  hksx := 0;
      [*] = ;                  hksz := 0;
      [*] = ;                  hkbest := 1000000;
      [*] = ;                  hkany := 1000000;
      [*] = ;                  hkrmin := 0;
      [*] = ;                  hkrmax := 0;
      [*] = ;                  gIntegerList.Clear;
      [*] = ;                  // The living of the remembered roll; range of OUR shooter from the first living man:
      [*] = ;                  // the longest enabled weapon of his kind (objbase carries the upgraded radius).
      [*] = ;                  var hkgn : Integer = ParserGetIntValueByKeyByHandle(hkgp, 'g' + IntToStr(hkgid) + '_n');
      [*] = ;                  for hkk := 0 to hkgn-1 do
      [*] = ;                  begin
      [*] = ;                     var hkh : Integer = ParserGetIntValueByKeyByHandle(hkgp, 'g' + IntToStr(hkgid) + '_h' + IntToStr(hkk));
      [*] = ;                     if (hkh <> 0) then
      [*] = ;                     begin
      [*] = ;                        var hkhp : Pointer = _unit_GetTObj(hkh);
      [*] = ;                        if (hkhp<>nil) then
      [*] = ;                        if (not TObj(hkhp).bdead) then
      [*] = ;                        begin
      [*] = ;                           gIntegerList.Add(hkh);
      [*] = ;                           hkn := hkn + 1;
      [*] = ;                           hksx := hksx + GetGameObjectPositionXByHandle(hkh);
      [*] = ;                           hksz := hksz + GetGameObjectPositionZByHandle(hkh);
      [*] = ;                           if (hkrmax <= 0) then
      [*] = ;                           for hkw := 0 to gc_obj_MaxWeapon-1 do
      [*] = ;                           if (gObjProp[TObj(hkhp).cid][TObj(hkhp).id].weapon[hkw].enabled) then
      [*] = ;                           if (gPlayer[plind].objbase[TObj(hkhp).cid][TObj(hkhp).id].weapon[hkw].radiusmax > hkrmax) then
      [*] = ;                           begin
      [*] = ;                              hkrmax := gPlayer[plind].objbase[TObj(hkhp).cid][TObj(hkhp).id].weapon[hkw].radiusmax;
      [*] = ;                              hkrmin := gObjProp[TObj(hkhp).cid][TObj(hkhp).id].weapon[hkw].radiusmin;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hkn = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_on', 0);
      [*] = ;                     Log('bridge-human: KITE group ' + IntToStr(hkgid) + ' off - nobody alive');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     hksx := hksx / hkn;
      [*] = ;                     hksz := hksz / hkn;
      [*] = ;                     // His nearest MELEE fighter (longest weapon no further than melee reach) decides the
      [*] = ;                     // step back; his nearest fighter of any kind decides whether there is anyone to shoot.
      [*] = ;                     // Same enemy scan as RETREAT's facing, same filters (no buildings, no peasants).
      [*] = ;                     for hkpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;                     if (gPlayer[hkpl].bexists) and (hkpl <> plind) then
      [*] = ;                     if ((gPlayer[plind].enemyPlMask and gPlayer[hkpl].myPlMask) <> 0) then
      [*] = ;                     begin
      [*] = ;                        var hkeph : Integer = GetPlayerHandleByIndex(hkpl);
      [*] = ;                        var hken : Integer = GetPlayerGameObjectsCountByHandle(hkeph);
      [*] = ;                        for hkj := 0 to hken-1 do
      [*] = ;                        begin
      [*] = ;                           var hkeg : Integer = GetGameObjectHandleByIndex(hkj, hkeph);
      [*] = ;                           var hkep : Pointer = _unit_GetTObj(hkeg);
      [*] = ;                           if (hkep<>nil) then
      [*] = ;                           if (not TObj(hkep).bdead) then
      [*] = ;                           if (not gObjProp[TObj(hkep).cid][TObj(hkep).id].bbuilding) then
      [*] = ;                           begin
      [*] = ;                              var hkeu : Integer = gObjProp[TObj(hkep).cid][TObj(hkep).id].usage;
      [*] = ;                              if (hkeu <> gc_obj_usage_peasant) and (hkeu <> gc_obj_usage_none) then
      [*] = ;                              begin
      [*] = ;                                 hked := VectorDistance(GetGameObjectPositionXByHandle(hkeg), 0,
      [*] = ;                                      GetGameObjectPositionZByHandle(hkeg), hksx, 0, hksz);
      [*] = ;                                 if (hked < hkany) then
      [*] = ;                                 hkany := hked;
      [*] = ;                                 hkerm := 0;
      [*] = ;                                 for hkw := 0 to gc_obj_MaxWeapon-1 do
      [*] = ;                                 if (gObjProp[TObj(hkep).cid][TObj(hkep).id].weapon[hkw].enabled) then
      [*] = ;                                 if (gPlayer[hkpl].objbase[TObj(hkep).cid][TObj(hkep).id].weapon[hkw].radiusmax > hkerm) then
      [*] = ;                                 hkerm := gPlayer[hkpl].objbase[TObj(hkep).cid][TObj(hkep).id].weapon[hkw].radiusmax;
      [*] = ;                                 if (hkerm <= gc_unit_meleeattackradius) and (hked < hkbest) then
      [*] = ;                                 begin
      [*] = ;                                    hkbest := hked;
      [*] = ;                                    hkex := GetGameObjectPositionXByHandle(hkeg);
      [*] = ;                                    hkez := GetGameObjectPositionZByHandle(hkeg);
      [*] = ;                                 end;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     var hkgap : Float = ParserGetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_gap10') / 10;
      [*] = ;                     var hkstep : Float = ParserGetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_step10') / 10;
      [*] = ;                     var hkfarr : Float = ParserGetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_far10') / 10;
      [*] = ;                     var hkst : Integer = ParserGetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_st');
      [*] = ;                     // Facing: towards his nearest melee man (towards his nearest anybody when no melee).
      [*] = ;                     var hkfx : Float = hkex - hksx;
      [*] = ;                     var hkfy : Float = 0;
      [*] = ;                     var hkfz : Float = hkez - hksz;
      [*] = ;                     if (hkbest >= 1000000) then
      [*] = ;                     begin
      [*] = ;                        hkfx := 0;
      [*] = ;                        hkfz := 1;
      [*] = ;                     end;
      [*] = ;                     if (VectorLength(hkfx, hkfy, hkfz) < 1) then
      [*] = ;                     begin
      [*] = ;                        hkfx := 0;
      [*] = ;                        hkfz := 1;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     VectorNormalize(hkfx, hkfy, hkfz);
      [*] = ;                     // Step direction: away from him, bent half towards the hall so the retreat curves
      [*] = ;                     // home instead of running the shooters off into the field (or into his second heap).
      [*] = ;                     var hkdx : Float = hksx - hkex;
      [*] = ;                     var hkdy : Float = 0;
      [*] = ;                     var hkdz : Float = hksz - hkez;
      [*] = ;                     if (VectorLength(hkdx, hkdy, hkdz) < 1) then
      [*] = ;                     begin
      [*] = ;                        hkdx := 0;
      [*] = ;                        hkdz := -1;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     VectorNormalize(hkdx, hkdy, hkdz);
      [*] = ;                     if (hkhall) then
      [*] = ;                     begin
      [*] = ;                        var hkhdx : Float = hkhx - hksx;
      [*] = ;                        var hkhdy : Float = 0;
      [*] = ;                        var hkhdz : Float = hkhz - hksz;
      [*] = ;                        if (VectorLength(hkhdx, hkhdy, hkhdz) > 4) then
      [*] = ;                        begin
      [*] = ;                           VectorNormalize(hkhdx, hkhdy, hkhdz);
      [*] = ;                           hkdx := hkdx + 0.5*hkhdx;
      [*] = ;                           hkdz := hkdz + 0.5*hkhdz;
      [*] = ;                           if (VectorLength(hkdx, hkdy, hkdz) < 0.1) then
      [*] = ;                           begin
      [*] = ;                              hkdx := hkhdx;
      [*] = ;                              hkdz := hkhdz;
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           VectorNormalize(hkdx, hkdy, hkdz);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     // 0 nothing, 1 step back to hktx,hktz, 2 hold here. Decided first, done once below.
      [*] = ;                     var hkdo : Integer = 0;
      [*] = ;                     var hktx : Float = hksx + hkdx*hkstep;
      [*] = ;                     var hktz : Float = hksz + hkdz*hkstep;
      [*] = ;                     var hkwhat : String = '';
      [*] = ;                     if (hkbest < hkrmin + hkgap) then
      [*] = ;                     begin
      [*] = ;                        var hkfar : Boolean = False;
      [*] = ;                        if (hkhall) then
      [*] = ;                        if (VectorDistance(hktx, 0, hktz, hkhx, 0, hkhz) > hkfarr) then hkfar := True;
      [*] = ;                        if (hkfar) then
      [*] = ;                        begin
      [*] = ;                           hkwhat := 'hold at the edge (' + IntToStr(Round(hkfarr)) + ' from the hall)';
      [*] = ;                           if (hkst <> 2) then hkdo := 2;
      [*] = ;                           hkst := 2;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           hkwhat := 'step back ' + IntToStr(Round(hkstep*10)) + '/10';
      [*] = ;                           hkdo := 1;
      [*] = ;                           hkst := 1;
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (hkany <= hkrmax + hkgap) then
      [*] = ;                     begin
      [*] = ;                        hkwhat := 'hold, fire';
      [*] = ;                        if (hkst <> 2) then hkdo := 2;
      [*] = ;                        hkst := 2;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                        hkwhat := 'hold, wait';
      [*] = ;                        if (hkst <> 3) then hkdo := 2;
      [*] = ;                        hkst := 3;
      [*] = ;                     end;
      [*] = ;                     if (hkdo > 0) then
      [*] = ;                     begin
      [*] = ;                        // The group object is rebuilt from the living before every order, exactly as the
      [*] = ;                        // order path does it; the hold goes AFTER the position call (WriteMove clears it).
      [*] = ;                        var hkgr : Integer = _misc_GetOrCreateGroupByName(hkph, 'coss3_grp_' + IntToStr(hkgid));
      [*] = ;                        GroupClearGameObjectsByHandle(hkgr);
      [*] = ;                        for hkk := 0 to gIntegerList.GetCount-1 do
      [*] = ;                        GroupAddGameObjectByHandle(hkgr, gIntegerList.Get(hkk));
      [*] = ;                        _group_Initialize(hkgr, nil);
      [*] = ;                        if (hkdo = 1) then
      [*] = ;                        begin
      [*] = ;                           _player_SetGroupPosition(hkph, hkgr, -1, hktx, hktz, hktx, hktz, hkfx, hkfz,
      [*] = ;                                False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           _player_SetGroupPosition(hkph, hkgr, -1, hksx, hksz, hksx, hksz, hkfx, hkfz,
      [*] = ;                                False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                           _misc_SetUnitsListUnitState(gIntegerList, True, False, True, False);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     ParserSetIntValueByKeyByHandle(hkp, 'g' + IntToStr(hkgid) + '_st', hkst);
      [*] = ;                     // One line a second while a group kites: this IS the live measurement the player
      [*] = ;                     // asked for - distance to his melee in tenths of a tile against our rmin/rmax.
      [*] = ;                     var hkbp : Integer = 9999;
      [*] = ;                     if (hkbest < 999) then hkbp := Round(hkbest*10);
      [*] = ;                     var hkap : Integer = 9999;
      [*] = ;                     if (hkany < 999) then hkap := Round(hkany*10);
      [*] = ;                     Log('bridge-human: KITE group ' + IntToStr(hkgid) + ' ' + hkwhat + ': ' + IntToStr(hkn) +
      [*] = ;                         ' shooters at ' + FloatToStr(hksx) + ',' + FloatToStr(hksz) +
      [*] = ;                         ' melee10=' + IntToStr(hkbp) + ' any10=' + IntToStr(hkap) +
      [*] = ;                         ' rmin10=' + IntToStr(Round(hkrmin*10)) + ' rmax10=' + IntToStr(Round(hkrmax*10)) + ' st=' + IntToStr(hkst));
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // === HOME DEFENCE REFLEX (30.10, mac, list item 1): once a second, without waiting for python ===
      [*] = ;      // Poland game 12:47-13:08: his 221 pikes stood 4 cells from our town hall, our 77 held the line (FACE hold) and the
      [*] = ;      // python's ATTACK by number was refused ('attack skipped 77 holding soldiers'); python looks once in 5 s. Here the
      [*] = ;      // block itself: enemy SOLDIERS within hdrad cells of our town hall >= hdmin -> every held soldier outside squads and
      [*] = ;      // (cells by Chebyshev - max of |dx|,|dz| - the same measure the python analysis uses for 'N cells from the town hall';
      [*] = ;      // the first build used a circle and missed a camp 4 cells away on the diagonal, 30.10 container copy 2)
      [*] = ;      // every squad of ours gets stand ground OFF and search victim ON, so they engage by themselves; repeated not more
      [*] = ;      // than once in 10 s while the enemy stays; logged. br_hdef keeps on<p>/t<p>/n<p> for the state block (defend_on,
      [*] = ;      // defend_n) and the switch defend<p> (1 by default; python may set 0 later through a command).
      [*] = ;      // Defence counters at block scope (17.09 lesson: a number declared in a nested begin does not accumulate).
      [*] = ;      var hdcx, hdcz : Float;
      [*] = ;      var hdcen : Boolean;
      [*] = ;      var hden, hdheld, hdsqn, hdoff, hdon : Integer;
      [*] = ;      var hdt, hdseen : Float;
      [*] = ;      var hdfire : Boolean;
      [*] = ;      var hdp : Integer = ParserSelectByKey('br_hdef');
      [*] = ;      if (hdp = 0) then
      [*] = ;      hdp := ParserCreate('br_hdef');
      [*] = ;      if (ParserGetValueByKeyByHandle(hdp, 'defend' + IntToStr(plind)) = '') then
      [*] = ;      ParserSetIntValueByKeyByHandle(hdp, 'defend' + IntToStr(plind), 1);
      [*] = ;      // TIME MARK (30.10, asked by Windows): LOG|N in game.log is a line number, not a second; one line per game second
      [*] = ;      // lets any bridge-human line be dated by the nearest mark above it. ABOVE the switch (30.10 evening, Windows: in the
      [*] = ;      // 'off' copies the clock died at TIME 60 - the mark has nothing to do with the reflex).
      [*] = ;      var hdnow : Float = GetGameTime;
      [*] = ;      var hdlast : Float = ParserGetFloatValueByKeyByHandle(hdp, 'chk' + IntToStr(plind));
      [*] = ;      var hdtick : Boolean = (hdnow - hdlast >= 1.0) or (hdnow < hdlast);
      [*] = ;      if (hdtick) then
      [*] = ;      begin
      [*] = ;         ParserSetFloatValueByKeyByHandle(hdp, 'chk' + IntToStr(plind), hdnow);
      [*] = ;         Log('bridge-human: TIME ' + IntToStr(Round(hdnow)));
      [*] = ;      end;
      [*] = ;      if (ParserGetIntValueByKeyByHandle(hdp, 'defend' + IntToStr(plind)) = 1) then
      [*] = ;      begin
      [*] = ;         if (hdtick) then
      [*] = ;         begin
      [*] = ;            var hdph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var hdoc : Integer = GetPlayerGameObjectsCountByHandle(hdph);
      [*] = ;            hdcx := 0;
      [*] = ;            hdcz := 0;
      [*] = ;            hdcen := False;
      [*] = ;            var hdk : Integer;
      [*] = ;            for hdk := 0 to hdoc-1 do
      [*] = ;            begin
      [*] = ;               var hdgo : Integer = GetGameObjectHandleByIndex(hdk, hdph);
      [*] = ;               var hdpo : Pointer = _unit_GetTObj(hdgo);
      [*] = ;               if (hdpo<>nil) then
      [*] = ;               if (not TObj(hdpo).bdead) then
      [*] = ;               if (gObjProp[TObj(hdpo).cid][TObj(hdpo).id].airole = gc_ai_unit_center) and (not hdcen) then
      [*] = ;               begin
      [*] = ;                  hdcen := True;
      [*] = ;                  hdcx := GetGameObjectPositionXByHandle(hdgo);
      [*] = ;                  hdcz := GetGameObjectPositionZByHandle(hdgo);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hdcen) then
      [*] = ;            begin
      [*] = ;               var hdrad : Float = 4.0 * GetMapWidth / 16.0;
      [*] = ;               var hdmin : Integer = 20;
      [*] = ;               hden := 0;
      [*] = ;               var hdpl : Integer;
      [*] = ;               for hdpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;               if (gPlayer[hdpl].bexists) and (hdpl <> plind) then
      [*] = ;               if ((gPlayer[plind].enemyPlMask and gPlayer[hdpl].myPlMask) <> 0) then
      [*] = ;               begin
      [*] = ;                  var hdeph : Integer = GetPlayerHandleByIndex(hdpl);
      [*] = ;                  var hdeoc : Integer = GetPlayerGameObjectsCountByHandle(hdeph);
      [*] = ;                  var hdj : Integer;
      [*] = ;                  for hdj := 0 to hdeoc-1 do
      [*] = ;                  begin
      [*] = ;                     var hdego : Integer = GetGameObjectHandleByIndex(hdj, hdeph);
      [*] = ;                     var hdepo : Pointer = _unit_GetTObj(hdego);
      [*] = ;                     if (hdepo<>nil) then
      [*] = ;                     if (not TObj(hdepo).bdead) then
      [*] = ;                     begin
      [*] = ;                        var hdeu : Integer = gObjProp[TObj(hdepo).cid][TObj(hdepo).id].usage;
      [*] = ;                        if (hdeu = gc_obj_usage_lightinfantry) or (hdeu = gc_obj_usage_weak) or (hdeu = gc_obj_usage_grenadier) or
      [*] = ;                           (hdeu = gc_obj_usage_shooter) or (hdeu = gc_obj_usage_archer) or (hdeu = gc_obj_usage_fasthorse) or
      [*] = ;                           (hdeu = gc_obj_usage_hardhorse) or (hdeu = gc_obj_usage_horseshooter) then
      [*] = ;                        begin
      [*] = ;                           var hddx : Float = GetGameObjectPositionXByHandle(hdego) - hdcx;
      [*] = ;                           var hddz : Float = GetGameObjectPositionZByHandle(hdego) - hdcz;
      [*] = ;                           if (hddx <= hdrad) and (hddx >= -hdrad) and (hddz <= hdrad) and (hddz >= -hdrad) then
      [*] = ;                           hden := hden + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               ParserSetIntValueByKeyByHandle(hdp, 'n' + IntToStr(plind), hden);
      [*] = ;               // HYSTERESIS (30.10, container s2): with the enemy standing still at 25-35 the count crossed 20 both ways and the
      [*] = ;               // reflex switched 8 times on and 4 times off in two minutes - the line went back to stand ground under fire. Now:
      [*] = ;               // on at >= hdmin (20), off only when the count has been below hdoff (12) for 30 s; while on, the flags are re-applied
      [*] = ;               // every 10 s silently (python's FACE of the tick may have re-held somebody). Game time is printed in every line.
      [*] = ;               hdoff := 12;
      [*] = ;               hdon := ParserGetIntValueByKeyByHandle(hdp, 'on' + IntToStr(plind));
      [*] = ;               hdt := ParserGetFloatValueByKeyByHandle(hdp, 't' + IntToStr(plind));
      [*] = ;               hdseen := ParserGetFloatValueByKeyByHandle(hdp, 'seen' + IntToStr(plind));
      [*] = ;               // STALE MATCH (4.11 evening, live game 2): br_hdef outlives the match. Without a game restart 'on' was 1 from the first
      [*] = ;               // tick with 0 enemies near, and the off-timer compared the clock with 'seen' of the previous game. A 'seen' or 't' in the
      [*] = ;               // future means a new game - start clean (python guards itself the same way: defend_on counts only with defend_n >= hdoff).
      [*] = ;               if (hdseen > hdnow) or (hdt > hdnow) then
      [*] = ;               begin
      [*] = ;               hdon := 0;
      [*] = ;               hdseen := 0;
      [*] = ;               hdt := 0;
      [*] = ;               ParserSetIntValueByKeyByHandle(hdp, 'on' + IntToStr(plind), 0);
      [*] = ;               ParserSetFloatValueByKeyByHandle(hdp, 'seen' + IntToStr(plind), 0);
      [*] = ;               ParserSetFloatValueByKeyByHandle(hdp, 't' + IntToStr(plind), 0);
      [*] = ;               Log('bridge-human: DEFENCE flags from a previous match dropped at ' + IntToStr(Round(hdnow)) + ' s');
      [*] = ;               end;
      [*] = ;               hdfire := False;
      [*] = ;               if (hden >= hdmin) then
      [*] = ;               begin
      [*] = ;                  ParserSetFloatValueByKeyByHandle(hdp, 'seen' + IntToStr(plind), hdnow);
      [*] = ;                  hdseen := hdnow;
      [*] = ;                  if (hdon = 0) then
      [*] = ;                  begin
      [*] = ;                     hdon := 1;
      [*] = ;                     hdfire := True;
      [*] = ;                     ParserSetIntValueByKeyByHandle(hdp, 'on' + IntToStr(plind), 1);
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hdon = 1) then
      [*] = ;               begin
      [*] = ;                  if (hden < hdoff) and (hdnow - hdseen >= 30.0) and (not hdfire) then
      [*] = ;                  begin
      [*] = ;                     ParserSetIntValueByKeyByHandle(hdp, 'on' + IntToStr(plind), 0);
      [*] = ;                     Log('bridge-human: DEFENCE over at ' + IntToStr(Round(hdnow)) + ' s - ' + IntToStr(hden) + ' enemy soldiers within 4 cells, below ' +
      [*] = ;                          IntToStr(hdoff) + ' for 30 s');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hdfire) or (hdnow - hdt >= 10.0) or (hdnow < hdt) then
      [*] = ;                  begin
      [*] = ;                     ParserSetFloatValueByKeyByHandle(hdp, 't' + IntToStr(plind), hdnow);
      [*] = ;                  hdheld := 0;
      [*] = ;                  hdsqn := 0;
      [*] = ;                  gIntegerList.Clear;
      [*] = ;                  for hdk := 0 to hdoc-1 do
      [*] = ;                  begin
      [*] = ;                     var hdgo2 : Integer = GetGameObjectHandleByIndex(hdk, hdph);
      [*] = ;                     var hdpo2 : Pointer = _unit_GetTObj(hdgo2);
      [*] = ;                     if (hdpo2<>nil) then
      [*] = ;                     if (not TObj(hdpo2).bdead) then
      [*] = ;                     if (TObj(hdpo2).squad < 0) and (TObj(hdpo2).bstandground) then
      [*] = ;                     begin
      [*] = ;                        var hdu2 : Integer = gObjProp[TObj(hdpo2).cid][TObj(hdpo2).id].usage;
      [*] = ;                        if (hdu2 = gc_obj_usage_lightinfantry) or (hdu2 = gc_obj_usage_weak) or (hdu2 = gc_obj_usage_grenadier) or
      [*] = ;                           (hdu2 = gc_obj_usage_shooter) or (hdu2 = gc_obj_usage_archer) or (hdu2 = gc_obj_usage_fasthorse) or
      [*] = ;                           (hdu2 = gc_obj_usage_hardhorse) or (hdu2 = gc_obj_usage_horseshooter) then
      [*] = ;                        begin
      [*] = ;                           gIntegerList.Add(hdgo2);
      [*] = ;                           hdheld := hdheld + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hdheld > 0) then
      [*] = ;                  _misc_SetUnitsListUnitState(gIntegerList, True, True, False, True);
      [*] = ;                  var hdsi : Integer;
      [*] = ;                  for hdsi := 0 to gPlayer[plind].squads.GetCount-1 do
      [*] = ;                  begin
      [*] = ;                     var hdsp : Pointer = gPlayer[plind].squads.Get(hdsi);
      [*] = ;                     if (hdsp<>nil) then
      [*] = ;                     begin
      [*] = ;                        TSquad(hdsp).fSearchVictim := True;
      [*] = ;                        TSquad(hdsp).fStandGround := False;
      [*] = ;                        var hdsj : Integer;
      [*] = ;                        for hdsj := 0 to TSquad(hdsp).GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hdsh : Integer = TSquad(hdsp).Get(hdsj);
      [*] = ;                           var hdsu : Pointer = _unit_GetTObj(hdsh);
      [*] = ;                           if (hdsu<>nil) then
      [*] = ;                           if (not TObj(hdsu).bdead) then
      [*] = ;                           begin
      [*] = ;                              TObj(hdsu).bsearchenemy := True;
      [*] = ;                              TObj(hdsu).bstandground := False;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        hdsqn := hdsqn + 1;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                     if (hdfire) then
      [*] = ;                     Log('bridge-human: DEFENCE at ' + IntToStr(Round(hdnow)) + ' s - ' + IntToStr(hden) + ' enemy soldiers within 4 cells of the town hall - released ' +
      [*] = ;                          IntToStr(hdheld) + ' held soldiers and ' + IntToStr(hdsqn) + ' squads to search victim');
      [*] = ;                     // mirrored into the state (31.10): last DEFENCE release -> hstate def_rel_t / def_rel_h / def_rel_s
      [*] = ;                     if (hdfire) then
      [*] = ;                     begin
      [*] = ;                        ParserSetIntValueByKeyByHandle(hdp, 'drt' + IntToStr(plind), Round(hdnow));
      [*] = ;                        ParserSetIntValueByKeyByHandle(hdp, 'drh' + IntToStr(plind), hdheld);
      [*] = ;                        ParserSetIntValueByKeyByHandle(hdp, 'drs' + IntToStr(plind), hdsqn);
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // HOLD ON ARRIVAL (31.10, list item 2): groups armed by MOVE arrive=1 are checked once a game second; when 4 of 5 alive
      [*] = ;      // remembered men stand idle within a cell of the target the hold is set (same call as FACE hold) and the group is mode 4.
      [*] = ;      // Not arrived in 180 s, or nobody alive - dropped, aloud.
      [*] = ;      var hgaidle : Integer = 0;
      [*] = ;      if (hdtick) then
      [*] = ;      begin
      [*] = ;         var hgap : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;         if (hgap <> 0) then
      [*] = ;         begin
      [*] = ;            var hgai : Integer;
      [*] = ;            for hgai := 0 to 7 do
      [*] = ;            begin
      [*] = ;               var hgag : Integer = ParserGetIntValueByKeyByHandle(hgap, 'hp' + IntToStr(hgai));
      [*] = ;               if (hgag > 0) then
      [*] = ;               begin
      [*] = ;                  var hgas : String = 'g' + IntToStr(hgag);
      [*] = ;                  if (ParserGetIntValueByKeyByHandle(hgap, hgas + '_ap') <> 1) then
      [*] = ;                  begin
      [*] = ;                     ParserSetIntValueByKeyByHandle(hgap, 'hp' + IntToStr(hgai), 0);
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hgax : Float = ParserGetFloatValueByKeyByHandle(hgap, hgas + '_ax');
      [*] = ;                     var hgaz : Float = ParserGetFloatValueByKeyByHandle(hgap, hgas + '_az');
      [*] = ;                     var hgat : Float = ParserGetFloatValueByKeyByHandle(hgap, hgas + '_at');
      [*] = ;                     var hgan : Integer = ParserGetIntValueByKeyByHandle(hgap, hgas + '_n');
      [*] = ;                     var hgacell : Float = GetMapWidth / 16;
      [*] = ;                     hgaidle := 0;
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     var hgak : Integer;
      [*] = ;                     for hgak := 0 to hgan-1 do
      [*] = ;                     begin
      [*] = ;                        var hgah : Integer = ParserGetIntValueByKeyByHandle(hgap, hgas + '_h' + IntToStr(hgak));
      [*] = ;                        var hgahp : Pointer = _unit_GetTObj(hgah);
      [*] = ;                        if (hgah <> 0) and (hgahp <> nil) then
      [*] = ;                        if (not TObj(hgahp).bdead) then
      [*] = ;                        begin
      [*] = ;                           gIntegerList.Add(hgah);
      [*] = ;                           if (TObj(hgahp).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                           if (VectorDistance(GetGameObjectPositionXByHandle(hgah), 0, GetGameObjectPositionZByHandle(hgah), hgax, 0, hgaz) <= hgacell) then
      [*] = ;                           hgaidle := hgaidle + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount > 0) and (hgaidle * 5 >= gIntegerList.GetCount * 4) then
      [*] = ;                     begin
      [*] = ;                        _misc_SetUnitsListUnitState(gIntegerList, True, False, True, False);
      [*] = ;                        ParserSetIntValueByKeyByHandle(hgap, hgas + '_ap', 0);
      [*] = ;                        ParserSetIntValueByKeyByHandle(hgap, hgas + '_m', 4);
      [*] = ;                        ParserSetIntValueByKeyByHandle(hgap, 'hp' + IntToStr(hgai), 0);
      [*] = ;                        Log('bridge-human: GROUP ' + IntToStr(hgag) + ' arrived at ' + FloatToStr(hgax) + ',' + FloatToStr(hgaz) + ': hold set on ' +
      [*] = ;                            IntToStr(gIntegerList.GetCount) + ' men (idle near ' + IntToStr(hgaidle) + ')');
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (hdnow - hgat > 180.0) or (gIntegerList.GetCount = 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetIntValueByKeyByHandle(hgap, hgas + '_ap', 0);
      [*] = ;                        ParserSetIntValueByKeyByHandle(hgap, 'hp' + IntToStr(hgai), 0);
      [*] = ;                        Log('bridge-human: GROUP ' + IntToStr(hgag) + ' hold on arrival dropped: not arrived in 180 s (alive ' +
      [*] = ;                            IntToStr(gIntegerList.GetCount) + ', idle near ' + IntToStr(hgaidle) + ')');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // RAID RETREAT (1.11): groups armed by ATTACK ret=N; when the time is up the living of the remembered roll walk home
      [*] = ;      // (move mode default - a walk, not a hunt; group mode 2), facing away from home. Nobody alive - dropped. Aloud either way.
      [*] = ;      if (hdtick) then
      [*] = ;      begin
      [*] = ;         var hgrp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;         if (hgrp <> 0) then
      [*] = ;         begin
      [*] = ;            var hgri : Integer;
      [*] = ;            for hgri := 0 to 7 do
      [*] = ;            begin
      [*] = ;               var hgrg : Integer = ParserGetIntValueByKeyByHandle(hgrp, 'rp' + IntToStr(hgri));
      [*] = ;               if (hgrg > 0) then
      [*] = ;               begin
      [*] = ;                  var hgrs : String = 'g' + IntToStr(hgrg);
      [*] = ;                  if (ParserGetIntValueByKeyByHandle(hgrp, hgrs + '_rq') <> 1) then
      [*] = ;                  begin
      [*] = ;                     ParserSetIntValueByKeyByHandle(hgrp, 'rp' + IntToStr(hgri), 0);
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hdnow >= ParserGetFloatValueByKeyByHandle(hgrp, hgrs + '_rt')) then
      [*] = ;                  begin
      [*] = ;                     var hgrx : Float = ParserGetFloatValueByKeyByHandle(hgrp, hgrs + '_rx');
      [*] = ;                     var hgrz : Float = ParserGetFloatValueByKeyByHandle(hgrp, hgrs + '_rz');
      [*] = ;                     var hgrn : Integer = ParserGetIntValueByKeyByHandle(hgrp, hgrs + '_n');
      [*] = ;                     var hgrsx : Float = 0;
      [*] = ;                     var hgrsz : Float = 0;
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     var hgrk : Integer;
      [*] = ;                     for hgrk := 0 to hgrn-1 do
      [*] = ;                     begin
      [*] = ;                        var hgrh : Integer = ParserGetIntValueByKeyByHandle(hgrp, hgrs + '_h' + IntToStr(hgrk));
      [*] = ;                        var hgrhp : Pointer = _unit_GetTObj(hgrh);
      [*] = ;                        if (hgrh <> 0) and (hgrhp <> nil) then
      [*] = ;                        if (not TObj(hgrhp).bdead) then
      [*] = ;                        begin
      [*] = ;                           gIntegerList.Add(hgrh);
      [*] = ;                           hgrsx := hgrsx + GetGameObjectPositionXByHandle(hgrh);
      [*] = ;                           hgrsz := hgrsz + GetGameObjectPositionZByHandle(hgrh);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount > 0) then
      [*] = ;                     begin
      [*] = ;                        // Facing: from the centre of the living towards home, normalised; degenerate (already home) keeps 0,1.
      [*] = ;                        var hgrdx : Float = hgrx - hgrsx / gIntegerList.GetCount;
      [*] = ;                        var hgrdz : Float = hgrz - hgrsz / gIntegerList.GetCount;
      [*] = ;                        var hgrdy : Float = 0;
      [*] = ;                        var hgrdl : Float = VectorLength(hgrdx, hgrdy, hgrdz);
      [*] = ;                        if (hgrdl < 1) then
      [*] = ;                        begin
      [*] = ;                           hgrdx := 0;
      [*] = ;                           hgrdz := 1;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           hgrdx := hgrdx / hgrdl;
      [*] = ;                           hgrdz := hgrdz / hgrdl;
      [*] = ;                        end;
      [*] = ;                        var hgrph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;                        var hgrgr : Integer = _misc_GetOrCreateGroupByName(hgrph, 'coss3_grp_' + IntToStr(hgrg));
      [*] = ;                        GroupClearGameObjectsByHandle(hgrgr);
      [*] = ;                        for hgrk := 0 to gIntegerList.GetCount-1 do
      [*] = ;                        GroupAddGameObjectByHandle(hgrgr, gIntegerList.Get(hgrk));
      [*] = ;                        _group_Initialize(hgrgr, nil);
      [*] = ;                        _player_SetGroupPosition(hgrph, hgrgr, -1, hgrx, hgrz, hgrx, hgrz, hgrdx, hgrdz,
      [*] = ;                             False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                        ParserSetIntValueByKeyByHandle(hgrp, hgrs + '_m', 2);
      [*] = ;                        Log('bridge-human: GROUP ' + IntToStr(hgrg) + ' retreat: ' + IntToStr(gIntegerList.GetCount) + ' men walk home to ' +
      [*] = ;                            FloatToStr(hgrx) + ',' + FloatToStr(hgrz));
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     Log('bridge-human: GROUP ' + IntToStr(hgrg) + ' retreat dropped: nobody alive');
      [*] = ;                     ParserSetIntValueByKeyByHandle(hgrp, hgrs + '_rq', 0);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hgrp, 'rp' + IntToStr(hgri), 0);
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE HUMAN COMMANDS ===