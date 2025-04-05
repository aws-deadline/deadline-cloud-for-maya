//Maya ASCII 2025ff03 scene
//Name: test.ma
//Last modified: Thu, Apr 03, 2025 04:44:56 am
//Codeset: UTF-8
requires -nodeType "simpleSelector" -nodeType "renderSetupLayer" -nodeType "renderSetup"
		 -nodeType "collection" -nodeType "shaderOverride" "renderSetup.py" "1.0";
currentUnit -l centimeter -a degree -t film;
fileInfo "application" "maya";
fileInfo "product" "Maya 2025";
fileInfo "version" "2025";
fileInfo "cutIdentifier" "202407121012-8ed02f4c99";
fileInfo "osv" "Mac OS X 15.1";
fileInfo "UUID" "F29A01ED-2C4B-E4CC-B18D-E1B82FE0220C";
createNode transform -s -n "top";
	rename -uid "AEB2013A-B949-5A00-2A2B-FAA3BABB8F5E";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 1000.1 0 ;
	setAttr ".r" -type "double3" -89.999999999999986 0 0 ;
createNode camera -s -n "topShape" -p "top";
	rename -uid "02C50896-BF42-C56F-5183-C796F563CF7F";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "top";
	setAttr ".den" -type "string" "top_depth";
	setAttr ".man" -type "string" "top_mask";
	setAttr ".hc" -type "string" "viewSet -t %camera";
	setAttr ".o" yes;
createNode transform -s -n "front";
	rename -uid "3E796583-7F49-8259-9CA7-F6B0A0200047";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 0 1000.1 ;
createNode camera -s -n "frontShape" -p "front";
	rename -uid "0800E50C-514C-3FE0-605D-AA81E3396959";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "front";
	setAttr ".den" -type "string" "front_depth";
	setAttr ".man" -type "string" "front_mask";
	setAttr ".hc" -type "string" "viewSet -f %camera";
	setAttr ".o" yes;
createNode transform -s -n "side";
	rename -uid "4C99D0F5-E04F-56C4-4F68-6C964DDB78EA";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 1000.1 0 0 ;
	setAttr ".r" -type "double3" 0 89.999999999999986 0 ;
createNode camera -s -n "sideShape" -p "side";
	rename -uid "D3713DD0-4C4B-2B7A-BAD7-34A972BF2A80";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "side";
	setAttr ".den" -type "string" "side_depth";
	setAttr ".man" -type "string" "side_mask";
	setAttr ".hc" -type "string" "viewSet -s %camera";
	setAttr ".o" yes;
createNode transform -n "movingSphere";
	rename -uid "533502C7-E64B-2817-A6D1-07B4D18B088D";
	setAttr -s 2 ".rlio";
	setAttr -s 2 ".rlio";
	setAttr ".t" -type "double3" 5 2 0 ;
createNode mesh -n "movingSphereShape" -p "movingSphere";
	rename -uid "CDDC2E55-2241-F264-A6A6-F29AC187A9A3";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Ambient+Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
createNode transform -n "topGrp";
	rename -uid "9A2E1C91-B348-52BF-B22C-678433D54778";
	setAttr -s 2 ".rlio";
	setAttr -s 2 ".rlio";
	setAttr ".t" -type "double3" 0 10 0 ;
	setAttr ".r" -type "double3" -45 0 0 ;
createNode transform -n "topCam1" -p "topGrp";
	rename -uid "2376E628-0F45-B202-1C3A-6396A024D003";
	setAttr ".t" -type "double3" -5.9061582145059228 6.6820552387804062 6.6820552387804169 ;
createNode camera -n "topCamShape1" -p "topCam1";
	rename -uid "8ABE9D24-2C48-4040-1E11-298195A32A6E";
	setAttr -k off ".v";
	setAttr ".coi" 16.143717031718325;
	setAttr ".imn" -type "string" "topCam1";
	setAttr ".den" -type "string" "topCam1_depth";
	setAttr ".man" -type "string" "topCam1_mask";
createNode aimConstraint -n "topCam1_aimConstraint1" -p "topCam1";
	rename -uid "0CEBFC0F-7441-D3B3-C6E7-BCB3E06B17B0";
	addAttr -dcb 0 -ci true -sn "w0" -ln "movingSphereW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 -1 ;
	setAttr ".rsrr" -type "double3" -45.000000000000007 0 0 ;
	setAttr -k on ".w0";
createNode transform -n "sideGrp";
	rename -uid "96CF2055-B648-6946-B4BE-67800F3F0965";
	setAttr -s 2 ".rlio";
	setAttr -s 2 ".rlio";
	setAttr ".t" -type "double3" 12 3 0 ;
createNode transform -n "sideCam1" -p "sideGrp";
	rename -uid "D621D5C6-DB41-341D-78E7-C99C486E70F1";
createNode camera -n "sideCamShape1" -p "sideCam1";
	rename -uid "7915BDEC-0C42-21C8-A6C3-068D583C7AC8";
	setAttr -k off ".v";
	setAttr ".imn" -type "string" "sideCam1";
	setAttr ".den" -type "string" "sideCam1_depth";
	setAttr ".man" -type "string" "sideCam1_mask";
createNode aimConstraint -n "sideCam1_aimConstraint1" -p "sideCam1";
	rename -uid "B3B73213-CA47-F41D-27A8-28BB2BC7D8A6";
	addAttr -dcb 0 -ci true -sn "w0" -ln "movingSphereW0" -dv 1 -at "double";
	setAttr -k on ".nds";
	setAttr -k off ".v";
	setAttr -k off ".tx";
	setAttr -k off ".ty";
	setAttr -k off ".tz";
	setAttr -k off ".rx";
	setAttr -k off ".ry";
	setAttr -k off ".rz";
	setAttr -k off ".sx";
	setAttr -k off ".sy";
	setAttr -k off ".sz";
	setAttr ".erp" yes;
	setAttr ".a" -type "double3" 0 0 -1 ;
	setAttr ".rsrr" -type "double3" -4.7636416907261792 89.999999999999972 0 ;
	setAttr -k on ".w0";
createNode transform -n "spotLight";
	rename -uid "50F88EE8-D648-C8DF-5E6A-DCBD4F5B872F";
	setAttr ".t" -type "double3" 5 12 0 ;
createNode spotLight -n "spotLightShape" -p "spotLight";
	rename -uid "0589CB4D-8E47-E954-7465-6695CB149F36";
	setAttr -k off ".v";
	setAttr -s 2 ".rlio";
	setAttr -s 2 ".rlio";
	setAttr ".in" 3;
	setAttr ".pa" 8;
	setAttr ".dro" 5;
createNode transform -n "background";
	rename -uid "3FBC31E7-2B42-8364-A2E4-A7928C928CF0";
	setAttr -s 2 ".rlio";
	setAttr -s 2 ".rlio";
createNode mesh -n "backgroundShape" -p "background";
	rename -uid "427B60E2-5A44-3EAE-3F17-F8B89E4C8FF4";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Ambient+Diffuse";
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
createNode lightLinker -s -n "lightLinker1";
	rename -uid "6C1771BF-E946-1704-B173-A3AF59E9643B";
	setAttr -s 3 ".lnk";
	setAttr -s 3 ".slnk";
createNode shapeEditorManager -n "shapeEditorManager";
	rename -uid "2141027E-BD4F-776A-B597-3EB1C47DA038";
createNode poseInterpolatorManager -n "poseInterpolatorManager";
	rename -uid "AB7BE5F3-464C-5040-EECC-E4BD40021D4B";
createNode displayLayerManager -n "layerManager";
	rename -uid "0D622772-B54F-11D7-1A9F-DC967DABB869";
createNode displayLayer -n "defaultLayer";
	rename -uid "885736A4-AA4A-134E-E27F-E58ABE4C92AB";
	setAttr ".ufem" -type "stringArray" 0  ;
createNode renderLayerManager -n "renderLayerManager";
	rename -uid "7240DA39-8246-7E20-DA0E-69A80940CA40";
	setAttr -s 3 ".rlmi[1:2]"  1 2;
	setAttr -s 3 ".rlmi";
createNode renderLayer -n "defaultRenderLayer";
	rename -uid "6A03CD2C-024A-3120-AAB9-96802C2D70B3";
	setAttr ".g" yes;
	setAttr ".rndr" no;
createNode polySphere -n "polySphere1";
	rename -uid "F4E4B696-874E-6205-5E46-85946F75C413";
	setAttr ".r" 2;
createNode checker -n "purpleCheckerTexture";
	rename -uid "1B19F781-7C43-2BFF-7BE8-3F893ECF4202";
	setAttr ".c1" -type "float3" 0.5 0 0.5 ;
	setAttr ".c2" -type "float3" 0.30000001 0 0.30000001 ;
createNode checker -n "orangeCheckerTexture";
	rename -uid "00F781F5-D64A-FEDA-C9F8-79BACAE8A8BB";
	setAttr ".c1" -type "float3" 1 0.5 0 ;
	setAttr ".c2" -type "float3" 0.69999999 0.34999999 0 ;
createNode place2dTexture -n "place2dTexture1";
	rename -uid "4B0DB22C-6D4D-24CB-36A3-319EDAB0486F";
createNode animCurveTL -n "movingSphere_translateX";
	rename -uid "7D639BB8-E943-5E7C-6A50-878A661CF54D";
	setAttr ".tan" 18;
	setAttr ".wgt" no;
	setAttr -s 25 ".ktv[0:24]"  1 5 2 4.8296291314453415 3 4.3301270189221936
		 4 3.5355339059327378 5 2.5000000000000004 6 1.2940952255126037 7 3.0616169978683831e-16
		 8 -1.2940952255126033 9 -2.4999999999999991 10 -3.5355339059327373 11 -4.3301270189221936
		 12 -4.8296291314453406 13 -5 14 -4.8296291314453415 15 -4.3301270189221945 16 -3.5355339059327395
		 17 -2.5000000000000022 18 -1.2940952255126033 19 -9.1848509936051479e-16 20 1.2940952255126015
		 21 2.5000000000000004 22 3.5355339059327369 23 4.3301270189221919 24 4.8296291314453406
		 25 5;
createNode animCurveTL -n "movingSphere_translateZ";
	rename -uid "6BA0ECC0-1C4B-D762-2851-64ADE73E9480";
	setAttr ".tan" 18;
	setAttr ".wgt" no;
	setAttr -s 25 ".ktv[0:24]"  1 0 2 1.2940952255126037 3 2.4999999999999996
		 4 3.5355339059327373 5 4.3301270189221928 6 4.8296291314453415 7 5 8 4.8296291314453415
		 9 4.3301270189221936 10 3.5355339059327378 11 2.4999999999999996 12 1.294095225512605
		 13 6.1232339957367663e-16 14 -1.2940952255126039 15 -2.4999999999999991 16 -3.5355339059327355
		 17 -4.3301270189221919 18 -4.8296291314453415 19 -5 20 -4.8296291314453423 21 -4.3301270189221928
		 22 -3.5355339059327386 23 -2.5000000000000022 24 -1.2940952255126079 25 -1.2246467991473533e-15;
createNode animCurveTL -n "spotLight_translateX";
	rename -uid "EEE54A60-264B-8CDA-5530-CE83463ADD2E";
	setAttr ".tan" 18;
	setAttr ".wgt" no;
	setAttr -s 25 ".ktv[0:24]"  1 5 2 4.8296291314453415 3 4.3301270189221936
		 4 3.5355339059327378 5 2.5000000000000004 6 1.2940952255126037 7 3.0616169978683831e-16
		 8 -1.2940952255126033 9 -2.4999999999999991 10 -3.5355339059327373 11 -4.3301270189221936
		 12 -4.8296291314453406 13 -5 14 -4.8296291314453415 15 -4.3301270189221945 16 -3.5355339059327395
		 17 -2.5000000000000022 18 -1.2940952255126033 19 -9.1848509936051479e-16 20 1.2940952255126015
		 21 2.5000000000000004 22 3.5355339059327369 23 4.3301270189221919 24 4.8296291314453406
		 25 5;
createNode animCurveTL -n "spotLight_translateZ";
	rename -uid "FF2E4B45-7E4C-1791-35BD-C7AB49561D76";
	setAttr ".tan" 18;
	setAttr ".wgt" no;
	setAttr -s 25 ".ktv[0:24]"  1 0 2 1.2940952255126037 3 2.4999999999999996
		 4 3.5355339059327373 5 4.3301270189221928 6 4.8296291314453415 7 5 8 4.8296291314453415
		 9 4.3301270189221936 10 3.5355339059327378 11 2.4999999999999996 12 1.294095225512605
		 13 6.1232339957367663e-16 14 -1.2940952255126039 15 -2.4999999999999991 16 -3.5355339059327355
		 17 -4.3301270189221919 18 -4.8296291314453415 19 -5 20 -4.8296291314453423 21 -4.3301270189221928
		 22 -3.5355339059327386 23 -2.5000000000000022 24 -1.2940952255126079 25 -1.2246467991473533e-15;
createNode polyPlane -n "polyPlane1";
	rename -uid "093A2218-D74D-AACB-BBDA-0CADEE67DA08";
	setAttr ".w" 30;
	setAttr ".h" 30;
createNode phong -n "purpleMaterial";
	rename -uid "E6E713BC-F34F-9BD0-0343-E093C223BFCF";
	setAttr ".sc" -type "float3" 1 1 1 ;
createNode phong -n "orangeMaterial";
	rename -uid "95CE68B2-0244-0A56-0E68-E48B78B6BD44";
	setAttr ".sc" -type "float3" 1 1 1 ;
createNode lambert -n "whiteMaterial";
	rename -uid "F3D82DED-484B-449B-5868-01ABB8692A51";
	setAttr ".c" -type "float3" 1 1 1 ;
createNode shadingEngine -n "whiteMaterialSG";
	rename -uid "6A221A73-B64B-CD69-FA92-84BFB2F1B80B";
	setAttr ".ihi" 0;
	setAttr ".ro" yes;
createNode materialInfo -n "materialInfo1";
	rename -uid "A242C714-3947-3E1E-443D-0CBC8E35DEBD";
createNode renderSetup -n "renderSetup";
	rename -uid "46C29828-FE4F-9F07-1A1E-3F9A8122B930";
createNode renderSetupLayer -n "purpleSphereLayer";
	rename -uid "13C88BE7-9943-D41B-2278-FFBACBA78C97";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode renderLayer -n "rs_purpleSphereLayer";
	rename -uid "E4AC3DA5-6D41-4624-7F98-369EE3CB3973";
	setAttr ".do" 1;
createNode renderSetupLayer -n "orangeSphereLayer";
	rename -uid "D2D88A66-B14F-C8D8-CEA8-2AA6AE8986E8";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode renderLayer -n "rs_orangeSphereLayer";
	rename -uid "055D06C9-0A45-57B3-2B0E-69B98422B4F5";
	setAttr ".do" 2;
createNode collection -n "purpleSphereCollection";
	rename -uid "D67055F5-164F-CB9D-72B7-22A33D1EC882";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "purpleSphereCollectionSelector";
	rename -uid "560137A3-2A4B-51B2-A35B-93A61FD7B03E";
	setAttr ".pat" -type "string" "movingSphere";
	setAttr ".ppa" -type "string" "movingSphere";
createNode collection -n "orangeSphereCollection";
	rename -uid "141776EA-0E46-0AE9-C1B0-89A3B1BAAF54";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "orangeSphereCollectionSelector";
	rename -uid "71815899-9243-58BF-D09F-438DB4227CD6";
	setAttr ".pat" -type "string" "movingSphere";
	setAttr ".ppa" -type "string" "movingSphere";
createNode collection -n "sphereCollection";
	rename -uid "C936ABA8-8E44-5B3B-1C25-41B7AF661F8B";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "sphereCollectionSelector";
	rename -uid "B2865B3E-D647-4816-06F7-F1A17ECC84BE";
	setAttr ".pat" -type "string" "movingSphere";
	setAttr ".ppa" -type "string" "movingSphere";
createNode shaderOverride -n "shaderOverride";
	rename -uid "B4DC65AF-3F4A-6CE2-0A0B-FBAD8FEFE457";
	addAttr -ci true -uac -sn "atv" -ln "attrValue" -at "float3" -nc 3;
	addAttr -ci true -sn "atvr" -ln "attrValueR" -at "float" -p "attrValue";
	addAttr -ci true -sn "atvg" -ln "attrValueG" -at "float" -p "attrValue";
	addAttr -ci true -sn "atvb" -ln "attrValueB" -at "float" -p "attrValue";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode collection -n "sphereCollection_shadingEngines";
	rename -uid "6AE4D0CB-544C-9EB0-A83E-0599B46D6AC1";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "sphereCollection_shadingEnginesSelector";
	rename -uid "115735D2-FC40-E5C5-2137-E5953F0AEC84";
	setAttr ".pat" -type "string" "*";
	setAttr ".ppa" -type "string" "*";
	setAttr ".tf" 11;
createNode collection -n "groundCollection";
	rename -uid "4E2F5FE2-BB49-0006-CFD2-19B99E10542C";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "groundCollectionSelector";
	rename -uid "67DB5385-794C-D837-3B6F-AEA03262627D";
	setAttr ".pat" -type "string" "background";
	setAttr ".ppa" -type "string" "background";
createNode collection -n "cameraCollection";
	rename -uid "22CEE189-7C48-7705-33E5-AF847A2F1CD6";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "cameraCollectionSelector";
	rename -uid "2183E6AA-D949-1A20-8E26-E98CE21ED270";
	setAttr ".pat" -type "string" "topCam1* sideCam1* topGrp sideGrp";
	setAttr ".ppa" -type "string" "topCam1* sideCam1* topGrp sideGrp";
createNode collection -n "lightCollection";
	rename -uid "7B19AC51-2546-7068-A0BA-06BC297C2633";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "lightCollectionSelector";
	rename -uid "D325C906-8840-8D11-150E-DA8619ACDFAD";
	setAttr ".pat" -type "string" "spotLightShape*";
	setAttr ".ppa" -type "string" "spotLightShape*";
createNode collection -n "sphereCollection1";
	rename -uid "39AC8F88-2E42-906D-DD12-02A657FFFB61";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "sphereCollection1Selector";
	rename -uid "EBF110C3-C347-66C1-5693-65B6CB52EED7";
	setAttr ".pat" -type "string" "movingSphere";
	setAttr ".ppa" -type "string" "movingSphere";
createNode shaderOverride -n "shaderOverride1";
	rename -uid "BB2D2B15-DA40-66FF-E8FC-00835CFEA5A7";
	addAttr -ci true -uac -sn "atv" -ln "attrValue" -at "float3" -nc 3;
	addAttr -ci true -sn "atvr" -ln "attrValueR" -at "float" -p "attrValue";
	addAttr -ci true -sn "atvg" -ln "attrValueG" -at "float" -p "attrValue";
	addAttr -ci true -sn "atvb" -ln "attrValueB" -at "float" -p "attrValue";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode collection -n "sphereCollection1_shadingEngines";
	rename -uid "7849C7B4-BD47-CBD0-77D7-409A2E8CE2BD";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "sphereCollection1_shadingEnginesSelector";
	rename -uid "E75683BC-8141-6484-9EF5-BBAD6A261EAA";
	setAttr ".pat" -type "string" "*";
	setAttr ".ppa" -type "string" "*";
	setAttr ".tf" 11;
createNode collection -n "groundCollection1";
	rename -uid "58E7EB7F-CA47-D40F-CC41-96A02E6099CF";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "groundCollection1Selector";
	rename -uid "B23CD598-1947-5FD1-B995-BBA5A85AC3FC";
	setAttr ".pat" -type "string" "background";
	setAttr ".ppa" -type "string" "background";
createNode collection -n "cameraCollection1";
	rename -uid "03CD5E56-0B4A-A2EC-C42F-CB93979BBC45";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "cameraCollection1Selector";
	rename -uid "3612F584-2E42-5455-406A-A8BC4623E44B";
	setAttr ".pat" -type "string" "topCam1* sideCam1* topGrp sideGrp";
createNode collection -n "lightCollection1";
	rename -uid "BDA9F11E-154E-770F-454B-50B24BEEE428";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "lightCollection1Selector";
	rename -uid "028C9BA9-2541-AC3D-D802-1FB53BAA2219";
	setAttr ".pat" -type "string" "spotLightShape*";
	setAttr ".ppa" -type "string" "spotLightShape*";
createNode collection -n "_untitled_";
	rename -uid "47A88D32-AF4C-348B-50E9-1194C48E5E7C";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "_untitled_Selector";
	rename -uid "565166E4-C042-D68E-F50B-D69D801915FF";
	setAttr ".ssl" -type "string" "|transform1";
createNode collection -n "_untitled_1";
	rename -uid "97569BB3-DF47-0325-87D3-C4A6753F1AB9";
	addAttr -ci true -sn "es" -ln "expandedState" -min 0 -max 1 -at "bool";
	setAttr ".es" yes;
createNode simpleSelector -n "_untitled_1Selector";
	rename -uid "9D238F80-4C40-9417-0CEE-5DAA6B53AF20";
	setAttr ".ssl" -type "string" "|transform1";
createNode script -n "uiConfigurationScriptNode";
	rename -uid "5FB5B1E2-FA4D-EF4A-3C09-B6B52DCBD4A6";
	setAttr ".b" -type "string" (
		"// Maya Mel UI Configuration File.\n//\n//  This script is machine generated.  Edit at your own risk.\n//\n//\n\nglobal string $gMainPane;\nif (`paneLayout -exists $gMainPane`) {\n\n\tglobal int $gUseScenePanelConfig;\n\tint    $useSceneConfig = $gUseScenePanelConfig;\n\tint    $nodeEditorPanelVisible = stringArrayContains(\"nodeEditorPanel1\", `getPanel -vis`);\n\tint    $nodeEditorWorkspaceControlOpen = (`workspaceControl -exists nodeEditorPanel1Window` && `workspaceControl -q -visible nodeEditorPanel1Window`);\n\tint    $menusOkayInPanels = `optionVar -q allowMenusInPanels`;\n\tint    $nVisPanes = `paneLayout -q -nvp $gMainPane`;\n\tint    $nPanes = 0;\n\tstring $editorName;\n\tstring $panelName;\n\tstring $itemFilterName;\n\tstring $panelConfig;\n\n\t//\n\t//  get current state of the UI\n\t//\n\tsceneUIReplacement -update $gMainPane;\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"modelPanel\" (localizedPanelLabel(\"Top View\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tmodelPanel -edit -l (localizedPanelLabel(\"Top View\")) -mbv $menusOkayInPanels  $panelName;\n"
		+ "\t\t$editorName = $panelName;\n        modelEditor -e \n            -camera \"|top\" \n            -useInteractiveMode 0\n            -displayLights \"default\" \n            -displayAppearance \"smoothShaded\" \n            -activeOnly 0\n            -ignorePanZoom 0\n            -wireframeOnShaded 0\n            -headsUpDisplay 1\n            -holdOuts 1\n            -selectionHiliteDisplay 1\n            -useDefaultMaterial 0\n            -bufferMode \"double\" \n            -twoSidedLighting 0\n            -backfaceCulling 0\n            -xray 0\n            -jointXray 0\n            -activeComponentsXray 0\n            -displayTextures 0\n            -smoothWireframe 0\n            -lineWidth 1\n            -textureAnisotropic 0\n            -textureHilight 1\n            -textureSampling 2\n            -textureDisplay \"modulate\" \n            -textureMaxSize 16384\n            -fogging 0\n            -fogSource \"fragment\" \n            -fogMode \"linear\" \n            -fogStart 0\n            -fogEnd 100\n            -fogDensity 0.1\n            -fogColor 0.5 0.5 0.5 1 \n"
		+ "            -depthOfFieldPreview 1\n            -maxConstantTransparency 1\n            -rendererName \"vp2Renderer\" \n            -objectFilterShowInHUD 1\n            -isFiltered 0\n            -colorResolution 256 256 \n            -bumpResolution 512 512 \n            -textureCompression 0\n            -transparencyAlgorithm \"frontAndBackCull\" \n            -transpInShadows 0\n            -cullingOverride \"none\" \n            -lowQualityLighting 0\n            -maximumNumHardwareLights 1\n            -occlusionCulling 0\n            -shadingModel 0\n            -useBaseRenderer 0\n            -useReducedRenderer 0\n            -smallObjectCulling 0\n            -smallObjectThreshold -1 \n            -interactiveDisableShadows 0\n            -interactiveBackFaceCull 0\n            -sortTransparent 1\n            -controllers 1\n            -nurbsCurves 1\n            -nurbsSurfaces 1\n            -polymeshes 1\n            -subdivSurfaces 1\n            -planes 1\n            -lights 1\n            -cameras 1\n            -controlVertices 1\n"
		+ "            -hulls 1\n            -grid 1\n            -imagePlane 1\n            -joints 1\n            -ikHandles 1\n            -deformers 1\n            -dynamics 1\n            -particleInstancers 1\n            -fluids 1\n            -hairSystems 1\n            -follicles 1\n            -nCloths 1\n            -nParticles 1\n            -nRigids 1\n            -dynamicConstraints 1\n            -locators 1\n            -manipulators 1\n            -pluginShapes 1\n            -dimensions 1\n            -handles 1\n            -pivots 1\n            -textures 1\n            -strokes 1\n            -motionTrails 1\n            -clipGhosts 1\n            -bluePencil 1\n            -greasePencils 0\n            -excludeObjectPreset \"All\" \n            -shadows 0\n            -captureSequenceNumber -1\n            -width 1\n            -height 1\n            -sceneRenderFilter 0\n            $editorName;\n        modelEditor -e -viewSelected 0 $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"modelPanel\" (localizedPanelLabel(\"Side View\")) `;\n"
		+ "\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tmodelPanel -edit -l (localizedPanelLabel(\"Side View\")) -mbv $menusOkayInPanels  $panelName;\n\t\t$editorName = $panelName;\n        modelEditor -e \n            -camera \"|side\" \n            -useInteractiveMode 0\n            -displayLights \"default\" \n            -displayAppearance \"smoothShaded\" \n            -activeOnly 0\n            -ignorePanZoom 0\n            -wireframeOnShaded 0\n            -headsUpDisplay 1\n            -holdOuts 1\n            -selectionHiliteDisplay 1\n            -useDefaultMaterial 0\n            -bufferMode \"double\" \n            -twoSidedLighting 0\n            -backfaceCulling 0\n            -xray 0\n            -jointXray 0\n            -activeComponentsXray 0\n            -displayTextures 0\n            -smoothWireframe 0\n            -lineWidth 1\n            -textureAnisotropic 0\n            -textureHilight 1\n            -textureSampling 2\n            -textureDisplay \"modulate\" \n            -textureMaxSize 16384\n            -fogging 0\n"
		+ "            -fogSource \"fragment\" \n            -fogMode \"linear\" \n            -fogStart 0\n            -fogEnd 100\n            -fogDensity 0.1\n            -fogColor 0.5 0.5 0.5 1 \n            -depthOfFieldPreview 1\n            -maxConstantTransparency 1\n            -rendererName \"vp2Renderer\" \n            -objectFilterShowInHUD 1\n            -isFiltered 0\n            -colorResolution 256 256 \n            -bumpResolution 512 512 \n            -textureCompression 0\n            -transparencyAlgorithm \"frontAndBackCull\" \n            -transpInShadows 0\n            -cullingOverride \"none\" \n            -lowQualityLighting 0\n            -maximumNumHardwareLights 1\n            -occlusionCulling 0\n            -shadingModel 0\n            -useBaseRenderer 0\n            -useReducedRenderer 0\n            -smallObjectCulling 0\n            -smallObjectThreshold -1 \n            -interactiveDisableShadows 0\n            -interactiveBackFaceCull 0\n            -sortTransparent 1\n            -controllers 1\n            -nurbsCurves 1\n"
		+ "            -nurbsSurfaces 1\n            -polymeshes 1\n            -subdivSurfaces 1\n            -planes 1\n            -lights 1\n            -cameras 1\n            -controlVertices 1\n            -hulls 1\n            -grid 1\n            -imagePlane 1\n            -joints 1\n            -ikHandles 1\n            -deformers 1\n            -dynamics 1\n            -particleInstancers 1\n            -fluids 1\n            -hairSystems 1\n            -follicles 1\n            -nCloths 1\n            -nParticles 1\n            -nRigids 1\n            -dynamicConstraints 1\n            -locators 1\n            -manipulators 1\n            -pluginShapes 1\n            -dimensions 1\n            -handles 1\n            -pivots 1\n            -textures 1\n            -strokes 1\n            -motionTrails 1\n            -clipGhosts 1\n            -bluePencil 1\n            -greasePencils 0\n            -excludeObjectPreset \"All\" \n            -shadows 0\n            -captureSequenceNumber -1\n            -width 1\n            -height 1\n            -sceneRenderFilter 0\n"
		+ "            $editorName;\n        modelEditor -e -viewSelected 0 $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"modelPanel\" (localizedPanelLabel(\"Front View\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tmodelPanel -edit -l (localizedPanelLabel(\"Front View\")) -mbv $menusOkayInPanels  $panelName;\n\t\t$editorName = $panelName;\n        modelEditor -e \n            -camera \"|front\" \n            -useInteractiveMode 0\n            -displayLights \"default\" \n            -displayAppearance \"smoothShaded\" \n            -activeOnly 0\n            -ignorePanZoom 0\n            -wireframeOnShaded 0\n            -headsUpDisplay 1\n            -holdOuts 1\n            -selectionHiliteDisplay 1\n            -useDefaultMaterial 0\n            -bufferMode \"double\" \n            -twoSidedLighting 0\n            -backfaceCulling 0\n            -xray 0\n            -jointXray 0\n            -activeComponentsXray 0\n            -displayTextures 0\n"
		+ "            -smoothWireframe 0\n            -lineWidth 1\n            -textureAnisotropic 0\n            -textureHilight 1\n            -textureSampling 2\n            -textureDisplay \"modulate\" \n            -textureMaxSize 16384\n            -fogging 0\n            -fogSource \"fragment\" \n            -fogMode \"linear\" \n            -fogStart 0\n            -fogEnd 100\n            -fogDensity 0.1\n            -fogColor 0.5 0.5 0.5 1 \n            -depthOfFieldPreview 1\n            -maxConstantTransparency 1\n            -rendererName \"vp2Renderer\" \n            -objectFilterShowInHUD 1\n            -isFiltered 0\n            -colorResolution 256 256 \n            -bumpResolution 512 512 \n            -textureCompression 0\n            -transparencyAlgorithm \"frontAndBackCull\" \n            -transpInShadows 0\n            -cullingOverride \"none\" \n            -lowQualityLighting 0\n            -maximumNumHardwareLights 1\n            -occlusionCulling 0\n            -shadingModel 0\n            -useBaseRenderer 0\n            -useReducedRenderer 0\n"
		+ "            -smallObjectCulling 0\n            -smallObjectThreshold -1 \n            -interactiveDisableShadows 0\n            -interactiveBackFaceCull 0\n            -sortTransparent 1\n            -controllers 1\n            -nurbsCurves 1\n            -nurbsSurfaces 1\n            -polymeshes 1\n            -subdivSurfaces 1\n            -planes 1\n            -lights 1\n            -cameras 1\n            -controlVertices 1\n            -hulls 1\n            -grid 1\n            -imagePlane 1\n            -joints 1\n            -ikHandles 1\n            -deformers 1\n            -dynamics 1\n            -particleInstancers 1\n            -fluids 1\n            -hairSystems 1\n            -follicles 1\n            -nCloths 1\n            -nParticles 1\n            -nRigids 1\n            -dynamicConstraints 1\n            -locators 1\n            -manipulators 1\n            -pluginShapes 1\n            -dimensions 1\n            -handles 1\n            -pivots 1\n            -textures 1\n            -strokes 1\n            -motionTrails 1\n            -clipGhosts 1\n"
		+ "            -bluePencil 1\n            -greasePencils 0\n            -excludeObjectPreset \"All\" \n            -shadows 0\n            -captureSequenceNumber -1\n            -width 1\n            -height 1\n            -sceneRenderFilter 0\n            $editorName;\n        modelEditor -e -viewSelected 0 $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"modelPanel\" (localizedPanelLabel(\"Persp View\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tmodelPanel -edit -l (localizedPanelLabel(\"Persp View\")) -mbv $menusOkayInPanels  $panelName;\n\t\t$editorName = $panelName;\n        modelEditor -e \n            -camera \"|topGrp|topCam1\" \n            -useInteractiveMode 0\n            -displayLights \"default\" \n            -displayAppearance \"smoothShaded\" \n            -activeOnly 0\n            -ignorePanZoom 0\n            -wireframeOnShaded 0\n            -headsUpDisplay 1\n            -holdOuts 1\n            -selectionHiliteDisplay 1\n"
		+ "            -useDefaultMaterial 0\n            -bufferMode \"double\" \n            -twoSidedLighting 0\n            -backfaceCulling 0\n            -xray 0\n            -jointXray 0\n            -activeComponentsXray 0\n            -displayTextures 0\n            -smoothWireframe 0\n            -lineWidth 1\n            -textureAnisotropic 0\n            -textureHilight 1\n            -textureSampling 2\n            -textureDisplay \"modulate\" \n            -textureMaxSize 16384\n            -fogging 0\n            -fogSource \"fragment\" \n            -fogMode \"linear\" \n            -fogStart 0\n            -fogEnd 100\n            -fogDensity 0.1\n            -fogColor 0.5 0.5 0.5 1 \n            -depthOfFieldPreview 1\n            -maxConstantTransparency 1\n            -rendererName \"vp2Renderer\" \n            -objectFilterShowInHUD 1\n            -isFiltered 0\n            -colorResolution 256 256 \n            -bumpResolution 512 512 \n            -textureCompression 0\n            -transparencyAlgorithm \"frontAndBackCull\" \n            -transpInShadows 0\n"
		+ "            -cullingOverride \"none\" \n            -lowQualityLighting 0\n            -maximumNumHardwareLights 1\n            -occlusionCulling 0\n            -shadingModel 0\n            -useBaseRenderer 0\n            -useReducedRenderer 0\n            -smallObjectCulling 0\n            -smallObjectThreshold -1 \n            -interactiveDisableShadows 0\n            -interactiveBackFaceCull 0\n            -sortTransparent 1\n            -controllers 1\n            -nurbsCurves 1\n            -nurbsSurfaces 1\n            -polymeshes 1\n            -subdivSurfaces 1\n            -planes 1\n            -lights 1\n            -cameras 1\n            -controlVertices 1\n            -hulls 1\n            -grid 1\n            -imagePlane 1\n            -joints 1\n            -ikHandles 1\n            -deformers 1\n            -dynamics 1\n            -particleInstancers 1\n            -fluids 1\n            -hairSystems 1\n            -follicles 1\n            -nCloths 1\n            -nParticles 1\n            -nRigids 1\n            -dynamicConstraints 1\n"
		+ "            -locators 1\n            -manipulators 1\n            -pluginShapes 1\n            -dimensions 1\n            -handles 1\n            -pivots 1\n            -textures 1\n            -strokes 1\n            -motionTrails 1\n            -clipGhosts 1\n            -bluePencil 1\n            -greasePencils 0\n            -excludeObjectPreset \"All\" \n            -shadows 0\n            -captureSequenceNumber -1\n            -width 2150\n            -height 1918\n            -sceneRenderFilter 0\n            $editorName;\n        modelEditor -e -viewSelected 0 $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"outlinerPanel\" (localizedPanelLabel(\"ToggledOutliner\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\toutlinerPanel -edit -l (localizedPanelLabel(\"ToggledOutliner\")) -mbv $menusOkayInPanels  $panelName;\n\t\t$editorName = $panelName;\n        outlinerEditor -e \n            -docTag \"isolOutln_fromSeln\" \n            -showShapes 0\n"
		+ "            -showAssignedMaterials 0\n            -showTimeEditor 1\n            -showReferenceNodes 1\n            -showReferenceMembers 1\n            -showAttributes 0\n            -showConnected 0\n            -showAnimCurvesOnly 0\n            -showMuteInfo 0\n            -organizeByLayer 1\n            -organizeByClip 1\n            -showAnimLayerWeight 1\n            -autoExpandLayers 1\n            -autoExpand 0\n            -showDagOnly 1\n            -showAssets 1\n            -showContainedOnly 1\n            -showPublishedAsConnected 0\n            -showParentContainers 0\n            -showContainerContents 1\n            -ignoreDagHierarchy 0\n            -expandConnections 0\n            -showUpstreamCurves 1\n            -showUnitlessCurves 1\n            -showCompounds 1\n            -showLeafs 1\n            -showNumericAttrsOnly 0\n            -highlightActive 1\n            -autoSelectNewObjects 0\n            -doNotSelectNewObjects 0\n            -dropIsParent 1\n            -transmitFilters 0\n            -setFilter \"defaultSetFilter\" \n"
		+ "            -showSetMembers 1\n            -allowMultiSelection 1\n            -alwaysToggleSelect 0\n            -directSelect 0\n            -isSet 0\n            -isSetMember 0\n            -showUfeItems 1\n            -displayMode \"DAG\" \n            -expandObjects 0\n            -setsIgnoreFilters 1\n            -containersIgnoreFilters 0\n            -editAttrName 0\n            -showAttrValues 0\n            -highlightSecondary 0\n            -showUVAttrsOnly 0\n            -showTextureNodesOnly 0\n            -attrAlphaOrder \"default\" \n            -animLayerFilterOptions \"allAffecting\" \n            -sortOrder \"none\" \n            -longNames 0\n            -niceNames 1\n            -showNamespace 1\n            -showPinIcons 0\n            -mapMotionTrails 0\n            -ignoreHiddenAttribute 0\n            -ignoreOutlinerColor 0\n            -renderFilterVisible 0\n            -renderFilterIndex 0\n            -selectionOrder \"chronological\" \n            -expandAttribute 0\n            $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n"
		+ "\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"outlinerPanel\" (localizedPanelLabel(\"Outliner\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\toutlinerPanel -edit -l (localizedPanelLabel(\"Outliner\")) -mbv $menusOkayInPanels  $panelName;\n\t\t$editorName = $panelName;\n        outlinerEditor -e \n            -showShapes 0\n            -showAssignedMaterials 0\n            -showTimeEditor 1\n            -showReferenceNodes 0\n            -showReferenceMembers 0\n            -showAttributes 0\n            -showConnected 0\n            -showAnimCurvesOnly 0\n            -showMuteInfo 0\n            -organizeByLayer 1\n            -organizeByClip 1\n            -showAnimLayerWeight 1\n            -autoExpandLayers 1\n            -autoExpand 0\n            -showDagOnly 1\n            -showAssets 1\n            -showContainedOnly 1\n            -showPublishedAsConnected 0\n            -showParentContainers 0\n            -showContainerContents 1\n            -ignoreDagHierarchy 0\n            -expandConnections 0\n"
		+ "            -showUpstreamCurves 1\n            -showUnitlessCurves 1\n            -showCompounds 1\n            -showLeafs 1\n            -showNumericAttrsOnly 0\n            -highlightActive 1\n            -autoSelectNewObjects 0\n            -doNotSelectNewObjects 0\n            -dropIsParent 1\n            -transmitFilters 0\n            -setFilter \"defaultSetFilter\" \n            -showSetMembers 1\n            -allowMultiSelection 1\n            -alwaysToggleSelect 0\n            -directSelect 0\n            -showUfeItems 1\n            -displayMode \"DAG\" \n            -expandObjects 0\n            -setsIgnoreFilters 1\n            -containersIgnoreFilters 0\n            -editAttrName 0\n            -showAttrValues 0\n            -highlightSecondary 0\n            -showUVAttrsOnly 0\n            -showTextureNodesOnly 0\n            -attrAlphaOrder \"default\" \n            -animLayerFilterOptions \"allAffecting\" \n            -sortOrder \"none\" \n            -longNames 0\n            -niceNames 1\n            -showNamespace 1\n            -showPinIcons 0\n"
		+ "            -mapMotionTrails 0\n            -ignoreHiddenAttribute 0\n            -ignoreOutlinerColor 0\n            -renderFilterVisible 0\n            $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"graphEditor\" (localizedPanelLabel(\"Graph Editor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Graph Editor\")) -mbv $menusOkayInPanels  $panelName;\n\n\t\t\t$editorName = ($panelName+\"OutlineEd\");\n            outlinerEditor -e \n                -showShapes 1\n                -showAssignedMaterials 0\n                -showTimeEditor 1\n                -showReferenceNodes 0\n                -showReferenceMembers 0\n                -showAttributes 1\n                -showConnected 1\n                -showAnimCurvesOnly 1\n                -showMuteInfo 0\n                -organizeByLayer 1\n                -organizeByClip 1\n                -showAnimLayerWeight 1\n                -autoExpandLayers 1\n"
		+ "                -autoExpand 1\n                -showDagOnly 0\n                -showAssets 1\n                -showContainedOnly 0\n                -showPublishedAsConnected 0\n                -showParentContainers 0\n                -showContainerContents 0\n                -ignoreDagHierarchy 0\n                -expandConnections 1\n                -showUpstreamCurves 1\n                -showUnitlessCurves 1\n                -showCompounds 0\n                -showLeafs 1\n                -showNumericAttrsOnly 1\n                -highlightActive 0\n                -autoSelectNewObjects 1\n                -doNotSelectNewObjects 0\n                -dropIsParent 1\n                -transmitFilters 1\n                -setFilter \"0\" \n                -showSetMembers 0\n                -allowMultiSelection 1\n                -alwaysToggleSelect 0\n                -directSelect 0\n                -showUfeItems 1\n                -displayMode \"DAG\" \n                -expandObjects 0\n                -setsIgnoreFilters 1\n                -containersIgnoreFilters 0\n"
		+ "                -editAttrName 0\n                -showAttrValues 0\n                -highlightSecondary 0\n                -showUVAttrsOnly 0\n                -showTextureNodesOnly 0\n                -attrAlphaOrder \"default\" \n                -animLayerFilterOptions \"allAffecting\" \n                -sortOrder \"none\" \n                -longNames 0\n                -niceNames 1\n                -showNamespace 1\n                -showPinIcons 1\n                -mapMotionTrails 1\n                -ignoreHiddenAttribute 0\n                -ignoreOutlinerColor 0\n                -renderFilterVisible 0\n                $editorName;\n\n\t\t\t$editorName = ($panelName+\"GraphEd\");\n            animCurveEditor -e \n                -displayValues 0\n                -snapTime \"integer\" \n                -snapValue \"none\" \n                -showPlayRangeShades \"on\" \n                -lockPlayRangeShades \"off\" \n                -smoothness \"fine\" \n                -resultSamples 1\n                -resultScreenSamples 0\n                -resultUpdate \"delayed\" \n"
		+ "                -showUpstreamCurves 1\n                -keyMinScale 1\n                -stackedCurvesMin -1\n                -stackedCurvesMax 1\n                -stackedCurvesSpace 0.2\n                -preSelectionHighlight 0\n                -limitToSelectedCurves 0\n                -constrainDrag 0\n                -valueLinesToggle 0\n                -highlightAffectedCurves 0\n                $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"dopeSheetPanel\" (localizedPanelLabel(\"Dope Sheet\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Dope Sheet\")) -mbv $menusOkayInPanels  $panelName;\n\n\t\t\t$editorName = ($panelName+\"OutlineEd\");\n            outlinerEditor -e \n                -showShapes 1\n                -showAssignedMaterials 0\n                -showTimeEditor 1\n                -showReferenceNodes 0\n                -showReferenceMembers 0\n                -showAttributes 1\n"
		+ "                -showConnected 1\n                -showAnimCurvesOnly 1\n                -showMuteInfo 0\n                -organizeByLayer 1\n                -organizeByClip 1\n                -showAnimLayerWeight 1\n                -autoExpandLayers 1\n                -autoExpand 1\n                -showDagOnly 0\n                -showAssets 1\n                -showContainedOnly 0\n                -showPublishedAsConnected 0\n                -showParentContainers 0\n                -showContainerContents 0\n                -ignoreDagHierarchy 0\n                -expandConnections 1\n                -showUpstreamCurves 1\n                -showUnitlessCurves 0\n                -showCompounds 0\n                -showLeafs 1\n                -showNumericAttrsOnly 1\n                -highlightActive 0\n                -autoSelectNewObjects 0\n                -doNotSelectNewObjects 1\n                -dropIsParent 1\n                -transmitFilters 0\n                -setFilter \"0\" \n                -showSetMembers 1\n                -allowMultiSelection 1\n"
		+ "                -alwaysToggleSelect 0\n                -directSelect 0\n                -showUfeItems 1\n                -displayMode \"DAG\" \n                -expandObjects 0\n                -setsIgnoreFilters 1\n                -containersIgnoreFilters 0\n                -editAttrName 0\n                -showAttrValues 0\n                -highlightSecondary 0\n                -showUVAttrsOnly 0\n                -showTextureNodesOnly 0\n                -attrAlphaOrder \"default\" \n                -animLayerFilterOptions \"allAffecting\" \n                -sortOrder \"none\" \n                -longNames 0\n                -niceNames 1\n                -showNamespace 1\n                -showPinIcons 0\n                -mapMotionTrails 1\n                -ignoreHiddenAttribute 0\n                -ignoreOutlinerColor 0\n                -renderFilterVisible 0\n                $editorName;\n\n\t\t\t$editorName = ($panelName+\"DopeSheetEd\");\n            dopeSheetEditor -e \n                -displayValues 0\n                -snapTime \"none\" \n                -snapValue \"none\" \n"
		+ "                -outliner \"dopeSheetPanel1OutlineEd\" \n                -hierarchyBelow 0\n                -selectionWindow 0 0 0 0 \n                $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"timeEditorPanel\" (localizedPanelLabel(\"Time Editor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Time Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"clipEditorPanel\" (localizedPanelLabel(\"Trax Editor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Trax Editor\")) -mbv $menusOkayInPanels  $panelName;\n\n\t\t\t$editorName = clipEditorNameFromPanel($panelName);\n            clipEditor -e \n                -displayValues 0\n                -snapTime \"none\" \n                -snapValue \"none\" \n"
		+ "                -initialized 0\n                -manageSequencer 0 \n                $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"sequenceEditorPanel\" (localizedPanelLabel(\"Camera Sequencer\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Camera Sequencer\")) -mbv $menusOkayInPanels  $panelName;\n\n\t\t\t$editorName = sequenceEditorNameFromPanel($panelName);\n            clipEditor -e \n                -displayValues 0\n                -snapTime \"none\" \n                -snapValue \"none\" \n                -initialized 0\n                -manageSequencer 1 \n                $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"hyperGraphPanel\" (localizedPanelLabel(\"Hypergraph Hierarchy\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Hypergraph Hierarchy\")) -mbv $menusOkayInPanels  $panelName;\n"
		+ "\n\t\t\t$editorName = ($panelName+\"HyperGraphEd\");\n            hyperGraph -e \n                -graphLayoutStyle \"hierarchicalLayout\" \n                -orientation \"horiz\" \n                -mergeConnections 0\n                -zoom 1\n                -animateTransition 0\n                -showRelationships 1\n                -showShapes 0\n                -showDeformers 0\n                -showExpressions 0\n                -showConstraints 0\n                -showConnectionFromSelected 0\n                -showConnectionToSelected 0\n                -showConstraintLabels 0\n                -showUnderworld 0\n                -showInvisible 0\n                -transitionFrames 1\n                -opaqueContainers 0\n                -freeform 0\n                -imagePosition 0 0 \n                -imageScale 1\n                -imageEnabled 0\n                -graphType \"DAG\" \n                -heatMapDisplay 0\n                -updateSelection 1\n                -updateNodeAdded 1\n                -useDrawOverrideColor 0\n                -limitGraphTraversal -1\n"
		+ "                -range 0 0 \n                -iconSize \"smallIcons\" \n                -showCachedConnections 0\n                $editorName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"hyperShadePanel\" (localizedPanelLabel(\"Hypershade\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Hypershade\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"visorPanel\" (localizedPanelLabel(\"Visor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Visor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"nodeEditorPanel\" (localizedPanelLabel(\"Node Editor\")) `;\n\tif ($nodeEditorPanelVisible || $nodeEditorWorkspaceControlOpen) {\n"
		+ "\t\tif (\"\" == $panelName) {\n\t\t\tif ($useSceneConfig) {\n\t\t\t\t$panelName = `scriptedPanel -unParent  -type \"nodeEditorPanel\" -l (localizedPanelLabel(\"Node Editor\")) -mbv $menusOkayInPanels `;\n\n\t\t\t$editorName = ($panelName+\"NodeEditorEd\");\n            nodeEditor -e \n                -allAttributes 0\n                -allNodes 0\n                -autoSizeNodes 1\n                -consistentNameSize 1\n                -createNodeCommand \"nodeEdCreateNodeCommand\" \n                -connectNodeOnCreation 0\n                -connectOnDrop 0\n                -copyConnectionsOnPaste 0\n                -connectionStyle \"bezier\" \n                -defaultPinnedState 0\n                -additiveGraphingMode 0\n                -connectedGraphingMode 1\n                -settingsChangedCallback \"nodeEdSyncControls\" \n                -traversalDepthLimit -1\n                -keyPressCommand \"nodeEdKeyPressCommand\" \n                -nodeTitleMode \"name\" \n                -gridSnap 0\n                -gridVisibility 1\n                -crosshairOnEdgeDragging 0\n"
		+ "                -popupMenuScript \"nodeEdBuildPanelMenus\" \n                -showNamespace 1\n                -showShapes 1\n                -showSGShapes 0\n                -showTransforms 1\n                -useAssets 1\n                -syncedSelection 1\n                -extendToShapes 1\n                -showUnitConversions 0\n                -editorMode \"default\" \n                -hasWatchpoint 0\n                $editorName;\n\t\t\t}\n\t\t} else {\n\t\t\t$label = `panel -q -label $panelName`;\n\t\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Node Editor\")) -mbv $menusOkayInPanels  $panelName;\n\n\t\t\t$editorName = ($panelName+\"NodeEditorEd\");\n            nodeEditor -e \n                -allAttributes 0\n                -allNodes 0\n                -autoSizeNodes 1\n                -consistentNameSize 1\n                -createNodeCommand \"nodeEdCreateNodeCommand\" \n                -connectNodeOnCreation 0\n                -connectOnDrop 0\n                -copyConnectionsOnPaste 0\n                -connectionStyle \"bezier\" \n                -defaultPinnedState 0\n"
		+ "                -additiveGraphingMode 0\n                -connectedGraphingMode 1\n                -settingsChangedCallback \"nodeEdSyncControls\" \n                -traversalDepthLimit -1\n                -keyPressCommand \"nodeEdKeyPressCommand\" \n                -nodeTitleMode \"name\" \n                -gridSnap 0\n                -gridVisibility 1\n                -crosshairOnEdgeDragging 0\n                -popupMenuScript \"nodeEdBuildPanelMenus\" \n                -showNamespace 1\n                -showShapes 1\n                -showSGShapes 0\n                -showTransforms 1\n                -useAssets 1\n                -syncedSelection 1\n                -extendToShapes 1\n                -showUnitConversions 0\n                -editorMode \"default\" \n                -hasWatchpoint 0\n                $editorName;\n\t\t\tif (!$useSceneConfig) {\n\t\t\t\tpanel -e -l $label $panelName;\n\t\t\t}\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"createNodePanel\" (localizedPanelLabel(\"Create Node\")) `;\n\tif (\"\" != $panelName) {\n"
		+ "\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Create Node\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"polyTexturePlacementPanel\" (localizedPanelLabel(\"UV Editor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"UV Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"renderWindowPanel\" (localizedPanelLabel(\"Render View\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Render View\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"shapePanel\" (localizedPanelLabel(\"Shape Editor\")) `;\n\tif (\"\" != $panelName) {\n"
		+ "\t\t$label = `panel -q -label $panelName`;\n\t\tshapePanel -edit -l (localizedPanelLabel(\"Shape Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextPanel \"posePanel\" (localizedPanelLabel(\"Pose Editor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tposePanel -edit -l (localizedPanelLabel(\"Pose Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"dynRelEdPanel\" (localizedPanelLabel(\"Dynamic Relationships\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Dynamic Relationships\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"relationshipPanel\" (localizedPanelLabel(\"Relationship Editor\")) `;\n"
		+ "\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Relationship Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"referenceEditorPanel\" (localizedPanelLabel(\"Reference Editor\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Reference Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"dynPaintScriptedPanelType\" (localizedPanelLabel(\"Paint Effects\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Paint Effects\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"scriptEditorPanel\" (localizedPanelLabel(\"Script Editor\")) `;\n"
		+ "\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Script Editor\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"profilerPanel\" (localizedPanelLabel(\"Profiler Tool\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Profiler Tool\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\t$panelName = `sceneUIReplacement -getNextScriptedPanel \"contentBrowserPanel\" (localizedPanelLabel(\"Content Browser\")) `;\n\tif (\"\" != $panelName) {\n\t\t$label = `panel -q -label $panelName`;\n\t\tscriptedPanel -edit -l (localizedPanelLabel(\"Content Browser\")) -mbv $menusOkayInPanels  $panelName;\n\t\tif (!$useSceneConfig) {\n\t\t\tpanel -e -l $label $panelName;\n\t\t}\n\t}\n\n\n\tif ($useSceneConfig) {\n        string $configName = `getPanel -cwl (localizedPanelLabel(\"Current Layout\"))`;\n"
		+ "        if (\"\" != $configName) {\n\t\t\tpanelConfiguration -edit -label (localizedPanelLabel(\"Current Layout\")) \n\t\t\t\t-userCreated false\n\t\t\t\t-defaultImage \"vacantCell.xP:/\"\n\t\t\t\t-image \"\"\n\t\t\t\t-sc false\n\t\t\t\t-configString \"global string $gMainPane; paneLayout -e -cn \\\"single\\\" -ps 1 100 100 $gMainPane;\"\n\t\t\t\t-removeAllPanels\n\t\t\t\t-ap false\n\t\t\t\t\t(localizedPanelLabel(\"Persp View\")) \n\t\t\t\t\t\"modelPanel\"\n"
		+ "\t\t\t\t\t\"$panelName = `modelPanel -unParent -l (localizedPanelLabel(\\\"Persp View\\\")) -mbv $menusOkayInPanels `;\\n$editorName = $panelName;\\nmodelEditor -e \\n    -camera \\\"|topGrp|topCam1\\\" \\n    -useInteractiveMode 0\\n    -displayLights \\\"default\\\" \\n    -displayAppearance \\\"smoothShaded\\\" \\n    -activeOnly 0\\n    -ignorePanZoom 0\\n    -wireframeOnShaded 0\\n    -headsUpDisplay 1\\n    -holdOuts 1\\n    -selectionHiliteDisplay 1\\n    -useDefaultMaterial 0\\n    -bufferMode \\\"double\\\" \\n    -twoSidedLighting 0\\n    -backfaceCulling 0\\n    -xray 0\\n    -jointXray 0\\n    -activeComponentsXray 0\\n    -displayTextures 0\\n    -smoothWireframe 0\\n    -lineWidth 1\\n    -textureAnisotropic 0\\n    -textureHilight 1\\n    -textureSampling 2\\n    -textureDisplay \\\"modulate\\\" \\n    -textureMaxSize 16384\\n    -fogging 0\\n    -fogSource \\\"fragment\\\" \\n    -fogMode \\\"linear\\\" \\n    -fogStart 0\\n    -fogEnd 100\\n    -fogDensity 0.1\\n    -fogColor 0.5 0.5 0.5 1 \\n    -depthOfFieldPreview 1\\n    -maxConstantTransparency 1\\n    -rendererName \\\"vp2Renderer\\\" \\n    -objectFilterShowInHUD 1\\n    -isFiltered 0\\n    -colorResolution 256 256 \\n    -bumpResolution 512 512 \\n    -textureCompression 0\\n    -transparencyAlgorithm \\\"frontAndBackCull\\\" \\n    -transpInShadows 0\\n    -cullingOverride \\\"none\\\" \\n    -lowQualityLighting 0\\n    -maximumNumHardwareLights 1\\n    -occlusionCulling 0\\n    -shadingModel 0\\n    -useBaseRenderer 0\\n    -useReducedRenderer 0\\n    -smallObjectCulling 0\\n    -smallObjectThreshold -1 \\n    -interactiveDisableShadows 0\\n    -interactiveBackFaceCull 0\\n    -sortTransparent 1\\n    -controllers 1\\n    -nurbsCurves 1\\n    -nurbsSurfaces 1\\n    -polymeshes 1\\n    -subdivSurfaces 1\\n    -planes 1\\n    -lights 1\\n    -cameras 1\\n    -controlVertices 1\\n    -hulls 1\\n    -grid 1\\n    -imagePlane 1\\n    -joints 1\\n    -ikHandles 1\\n    -deformers 1\\n    -dynamics 1\\n    -particleInstancers 1\\n    -fluids 1\\n    -hairSystems 1\\n    -follicles 1\\n    -nCloths 1\\n    -nParticles 1\\n    -nRigids 1\\n    -dynamicConstraints 1\\n    -locators 1\\n    -manipulators 1\\n    -pluginShapes 1\\n    -dimensions 1\\n    -handles 1\\n    -pivots 1\\n    -textures 1\\n    -strokes 1\\n    -motionTrails 1\\n    -clipGhosts 1\\n    -bluePencil 1\\n    -greasePencils 0\\n    -excludeObjectPreset \\\"All\\\" \\n    -shadows 0\\n    -captureSequenceNumber -1\\n    -width 2150\\n    -height 1918\\n    -sceneRenderFilter 0\\n    $editorName;\\nmodelEditor -e -viewSelected 0 $editorName\"\n"
		+ "\t\t\t\t\t\"modelPanel -edit -l (localizedPanelLabel(\\\"Persp View\\\")) -mbv $menusOkayInPanels  $panelName;\\n$editorName = $panelName;\\nmodelEditor -e \\n    -camera \\\"|topGrp|topCam1\\\" \\n    -useInteractiveMode 0\\n    -displayLights \\\"default\\\" \\n    -displayAppearance \\\"smoothShaded\\\" \\n    -activeOnly 0\\n    -ignorePanZoom 0\\n    -wireframeOnShaded 0\\n    -headsUpDisplay 1\\n    -holdOuts 1\\n    -selectionHiliteDisplay 1\\n    -useDefaultMaterial 0\\n    -bufferMode \\\"double\\\" \\n    -twoSidedLighting 0\\n    -backfaceCulling 0\\n    -xray 0\\n    -jointXray 0\\n    -activeComponentsXray 0\\n    -displayTextures 0\\n    -smoothWireframe 0\\n    -lineWidth 1\\n    -textureAnisotropic 0\\n    -textureHilight 1\\n    -textureSampling 2\\n    -textureDisplay \\\"modulate\\\" \\n    -textureMaxSize 16384\\n    -fogging 0\\n    -fogSource \\\"fragment\\\" \\n    -fogMode \\\"linear\\\" \\n    -fogStart 0\\n    -fogEnd 100\\n    -fogDensity 0.1\\n    -fogColor 0.5 0.5 0.5 1 \\n    -depthOfFieldPreview 1\\n    -maxConstantTransparency 1\\n    -rendererName \\\"vp2Renderer\\\" \\n    -objectFilterShowInHUD 1\\n    -isFiltered 0\\n    -colorResolution 256 256 \\n    -bumpResolution 512 512 \\n    -textureCompression 0\\n    -transparencyAlgorithm \\\"frontAndBackCull\\\" \\n    -transpInShadows 0\\n    -cullingOverride \\\"none\\\" \\n    -lowQualityLighting 0\\n    -maximumNumHardwareLights 1\\n    -occlusionCulling 0\\n    -shadingModel 0\\n    -useBaseRenderer 0\\n    -useReducedRenderer 0\\n    -smallObjectCulling 0\\n    -smallObjectThreshold -1 \\n    -interactiveDisableShadows 0\\n    -interactiveBackFaceCull 0\\n    -sortTransparent 1\\n    -controllers 1\\n    -nurbsCurves 1\\n    -nurbsSurfaces 1\\n    -polymeshes 1\\n    -subdivSurfaces 1\\n    -planes 1\\n    -lights 1\\n    -cameras 1\\n    -controlVertices 1\\n    -hulls 1\\n    -grid 1\\n    -imagePlane 1\\n    -joints 1\\n    -ikHandles 1\\n    -deformers 1\\n    -dynamics 1\\n    -particleInstancers 1\\n    -fluids 1\\n    -hairSystems 1\\n    -follicles 1\\n    -nCloths 1\\n    -nParticles 1\\n    -nRigids 1\\n    -dynamicConstraints 1\\n    -locators 1\\n    -manipulators 1\\n    -pluginShapes 1\\n    -dimensions 1\\n    -handles 1\\n    -pivots 1\\n    -textures 1\\n    -strokes 1\\n    -motionTrails 1\\n    -clipGhosts 1\\n    -bluePencil 1\\n    -greasePencils 0\\n    -excludeObjectPreset \\\"All\\\" \\n    -shadows 0\\n    -captureSequenceNumber -1\\n    -width 2150\\n    -height 1918\\n    -sceneRenderFilter 0\\n    $editorName;\\nmodelEditor -e -viewSelected 0 $editorName\"\n"
		+ "\t\t\t\t$configName;\n\n            setNamedPanelLayout (localizedPanelLabel(\"Current Layout\"));\n        }\n\n        panelHistory -e -clear mainPanelHistory;\n        sceneUIReplacement -clear;\n\t}\n\n\ngrid -spacing 5 -size 12 -divisions 5 -displayAxes yes -displayGridLines yes -displayDivisionLines yes -displayPerspectiveLabels no -displayOrthographicLabels no -displayAxesBold yes -perspectiveLabelPosition axis -orthographicLabelPosition edge;\nviewManip -drawCompass 0 -compassAngle 0 -frontParameters \"\" -homeParameters \"\" -selectionLockParameters \"\";\n}\n");
	setAttr ".st" 3;
createNode script -n "sceneConfigurationScriptNode";
	rename -uid "9B589FB7-7548-6482-04CA-D68518A81887";
	setAttr ".b" -type "string" "playbackOptions -min 1 -max 24 -ast 0 -aet 48 ";
	setAttr ".st" 6;
select -ne :time1;
	setAttr ".o" 1;
	setAttr ".unw" 1;
select -ne :hardwareRenderingGlobals;
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr ".aasc" 4;
	setAttr ".fprt" yes;
	setAttr ".rtfm" 3;
select -ne :renderPartition;
	setAttr -s 3 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 8 ".s";
select -ne :postProcessList1;
	setAttr -s 2 ".p";
select -ne :defaultRenderUtilityList1;
select -ne :defaultRenderingList1;
	setAttr -s 3 ".r";
select -ne :lightList1;
select -ne :defaultTextureList1;
	setAttr -s 2 ".tx";
select -ne :standardSurface1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :initialShadingGroup;
	setAttr ".ro" yes;
select -ne :initialParticleSE;
	setAttr ".ro" yes;
select -ne :initialMaterialInfo;
select -ne :defaultRenderGlobals;
	addAttr -ci true -h true -sn "dss" -ln "defaultSurfaceShader" -dt "string";
	setAttr ".ren" -type "string" "mayaHardware2";
	setAttr ".an" yes;
	setAttr ".fs" 5;
	setAttr ".pff" yes;
	setAttr ".peie" 2;
	setAttr ".ifp" -type "string" "<RenderLayer>_<Camera>";
	setAttr ".dss" -type "string" "standardSurface1";
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :defaultLightSet;
select -ne :defaultColorMgtGlobals;
	setAttr ".cfe" yes;
	setAttr ".cfp" -type "string" "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio";
	setAttr ".vtn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".vn" -type "string" "ACES 1.0 SDR-video";
	setAttr ".dn" -type "string" "sRGB";
	setAttr ".wsn" -type "string" "ACEScg";
	setAttr ".otn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".potn" -type "string" "ACES 1.0 SDR-video (sRGB)";
select -ne :hardwareRenderGlobals;
	setAttr ".ctrs" 256;
	setAttr ".btrs" 512;
connectAttr "movingSphere_translateX.o" "movingSphere.tx";
connectAttr "movingSphere_translateZ.o" "movingSphere.tz";
connectAttr "rs_orangeSphereLayer.ri" "movingSphere.rlio[0]";
connectAttr "rs_purpleSphereLayer.ri" "movingSphere.rlio[1]";
connectAttr "polySphere1.out" "movingSphereShape.i";
connectAttr "rs_orangeSphereLayer.ri" "topGrp.rlio[0]";
connectAttr "rs_purpleSphereLayer.ri" "topGrp.rlio[1]";
connectAttr "topCam1_aimConstraint1.crx" "topCam1.rx";
connectAttr "topCam1_aimConstraint1.cry" "topCam1.ry";
connectAttr "topCam1_aimConstraint1.crz" "topCam1.rz";
connectAttr "topCam1.pim" "topCam1_aimConstraint1.cpim";
connectAttr "topCam1.t" "topCam1_aimConstraint1.ct";
connectAttr "topCam1.rp" "topCam1_aimConstraint1.crp";
connectAttr "topCam1.rpt" "topCam1_aimConstraint1.crt";
connectAttr "topCam1.ro" "topCam1_aimConstraint1.cro";
connectAttr "movingSphere.t" "topCam1_aimConstraint1.tg[0].tt";
connectAttr "movingSphere.rp" "topCam1_aimConstraint1.tg[0].trp";
connectAttr "movingSphere.rpt" "topCam1_aimConstraint1.tg[0].trt";
connectAttr "movingSphere.pm" "topCam1_aimConstraint1.tg[0].tpm";
connectAttr "topCam1_aimConstraint1.w0" "topCam1_aimConstraint1.tg[0].tw";
connectAttr "rs_orangeSphereLayer.ri" "sideGrp.rlio[0]";
connectAttr "rs_purpleSphereLayer.ri" "sideGrp.rlio[1]";
connectAttr "sideCam1_aimConstraint1.crx" "sideCam1.rx";
connectAttr "sideCam1_aimConstraint1.cry" "sideCam1.ry";
connectAttr "sideCam1_aimConstraint1.crz" "sideCam1.rz";
connectAttr "sideCam1.pim" "sideCam1_aimConstraint1.cpim";
connectAttr "sideCam1.t" "sideCam1_aimConstraint1.ct";
connectAttr "sideCam1.rp" "sideCam1_aimConstraint1.crp";
connectAttr "sideCam1.rpt" "sideCam1_aimConstraint1.crt";
connectAttr "sideCam1.ro" "sideCam1_aimConstraint1.cro";
connectAttr "movingSphere.t" "sideCam1_aimConstraint1.tg[0].tt";
connectAttr "movingSphere.rp" "sideCam1_aimConstraint1.tg[0].trp";
connectAttr "movingSphere.rpt" "sideCam1_aimConstraint1.tg[0].trt";
connectAttr "movingSphere.pm" "sideCam1_aimConstraint1.tg[0].tpm";
connectAttr "sideCam1_aimConstraint1.w0" "sideCam1_aimConstraint1.tg[0].tw";
connectAttr "spotLight_translateX.o" "spotLight.tx";
connectAttr "spotLight_translateZ.o" "spotLight.tz";
connectAttr "rs_orangeSphereLayer.ri" "spotLightShape.rlio[0]";
connectAttr "rs_purpleSphereLayer.ri" "spotLightShape.rlio[1]";
connectAttr "rs_orangeSphereLayer.ri" "background.rlio[0]";
connectAttr "rs_purpleSphereLayer.ri" "background.rlio[1]";
connectAttr "polyPlane1.out" "backgroundShape.i";
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" "whiteMaterialSG.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" "whiteMaterialSG.message" ":defaultLightSet.message";
connectAttr "layerManager.dli[0]" "defaultLayer.id";
connectAttr "renderLayerManager.rlmi[0]" "defaultRenderLayer.rlid";
connectAttr "place2dTexture1.o" "purpleCheckerTexture.uv";
connectAttr "place2dTexture1.ofs" "purpleCheckerTexture.fs";
connectAttr "place2dTexture1.o" "orangeCheckerTexture.uv";
connectAttr "place2dTexture1.ofs" "orangeCheckerTexture.fs";
connectAttr "purpleCheckerTexture.oc" "purpleMaterial.c";
connectAttr "orangeCheckerTexture.oc" "orangeMaterial.c";
connectAttr "whiteMaterial.oc" "whiteMaterialSG.ss";
connectAttr "backgroundShape.iog" "whiteMaterialSG.dsm" -na;
connectAttr "whiteMaterialSG.msg" "materialInfo1.sg";
connectAttr "whiteMaterial.msg" "materialInfo1.m";
connectAttr "purpleSphereLayer.msg" "renderSetup.frl";
connectAttr "orangeSphereLayer.msg" "renderSetup.lrl";
connectAttr "rs_purpleSphereLayer.msg" "purpleSphereLayer.lrl";
connectAttr "renderSetup.lit" "purpleSphereLayer.pls";
connectAttr "_untitled_1.msg" "purpleSphereLayer.cl";
connectAttr "lightCollection.msg" "purpleSphereLayer.ch";
connectAttr "renderLayerManager.rlmi[1]" "rs_purpleSphereLayer.rlid";
connectAttr "rs_orangeSphereLayer.msg" "orangeSphereLayer.lrl";
connectAttr "purpleSphereLayer.nxt" "orangeSphereLayer.prv";
connectAttr "renderSetup.lit" "orangeSphereLayer.pls";
connectAttr "_untitled_.msg" "orangeSphereLayer.cl";
connectAttr "lightCollection1.msg" "orangeSphereLayer.ch";
connectAttr "renderLayerManager.rlmi[2]" "rs_orangeSphereLayer.rlid";
connectAttr "purpleSphereCollectionSelector.c" "purpleSphereCollection.sel";
connectAttr "purpleSphereLayer.lit" "purpleSphereCollection.pls";
connectAttr "purpleSphereLayer.nic" "purpleSphereCollection.pic";
connectAttr "_untitled_1.nxt" "purpleSphereCollection.prv";
connectAttr "orangeSphereCollectionSelector.c" "orangeSphereCollection.sel";
connectAttr "orangeSphereLayer.lit" "orangeSphereCollection.pls";
connectAttr "orangeSphereLayer.nic" "orangeSphereCollection.pic";
connectAttr "_untitled_.nxt" "orangeSphereCollection.prv";
connectAttr "sphereCollectionSelector.c" "sphereCollection.sel";
connectAttr "purpleSphereCollection.nxt" "sphereCollection.prv";
connectAttr "purpleSphereLayer.lit" "sphereCollection.pls";
connectAttr "purpleSphereLayer.nic" "sphereCollection.pic";
connectAttr "sphereCollection_shadingEngines.msg" "sphereCollection.cl";
connectAttr "sphereCollection_shadingEngines.msg" "sphereCollection.ch";
connectAttr "sphereCollection_shadingEngines.lit" "shaderOverride.pls";
connectAttr "sphereCollection_shadingEngines.en" "shaderOverride.pen";
connectAttr "purpleMaterial.oc" "shaderOverride.atv";
connectAttr "sphereCollection_shadingEnginesSelector.c" "sphereCollection_shadingEngines.sel"
		;
connectAttr "sphereCollection.lit" "sphereCollection_shadingEngines.pls";
connectAttr "sphereCollection.en" "sphereCollection_shadingEngines.pen";
connectAttr "purpleSphereLayer.nic" "sphereCollection_shadingEngines.pic";
connectAttr "shaderOverride.msg" "sphereCollection_shadingEngines.cl";
connectAttr "shaderOverride.msg" "sphereCollection_shadingEngines.ch";
connectAttr "sphereCollectionSelector.out" "sphereCollection_shadingEnginesSelector.in"
		;
connectAttr "groundCollectionSelector.c" "groundCollection.sel";
connectAttr "sphereCollection.nxt" "groundCollection.prv";
connectAttr "purpleSphereLayer.lit" "groundCollection.pls";
connectAttr "purpleSphereLayer.nic" "groundCollection.pic";
connectAttr "cameraCollectionSelector.c" "cameraCollection.sel";
connectAttr "groundCollection.nxt" "cameraCollection.prv";
connectAttr "purpleSphereLayer.lit" "cameraCollection.pls";
connectAttr "purpleSphereLayer.nic" "cameraCollection.pic";
connectAttr "lightCollectionSelector.c" "lightCollection.sel";
connectAttr "cameraCollection.nxt" "lightCollection.prv";
connectAttr "purpleSphereLayer.lit" "lightCollection.pls";
connectAttr "purpleSphereLayer.nic" "lightCollection.pic";
connectAttr "sphereCollection1Selector.c" "sphereCollection1.sel";
connectAttr "orangeSphereCollection.nxt" "sphereCollection1.prv";
connectAttr "orangeSphereLayer.lit" "sphereCollection1.pls";
connectAttr "orangeSphereLayer.nic" "sphereCollection1.pic";
connectAttr "sphereCollection1_shadingEngines.msg" "sphereCollection1.cl";
connectAttr "sphereCollection1_shadingEngines.msg" "sphereCollection1.ch";
connectAttr "sphereCollection1_shadingEngines.lit" "shaderOverride1.pls";
connectAttr "sphereCollection1_shadingEngines.en" "shaderOverride1.pen";
connectAttr "orangeMaterial.oc" "shaderOverride1.atv";
connectAttr "sphereCollection1_shadingEnginesSelector.c" "sphereCollection1_shadingEngines.sel"
		;
connectAttr "sphereCollection1.lit" "sphereCollection1_shadingEngines.pls";
connectAttr "sphereCollection1.en" "sphereCollection1_shadingEngines.pen";
connectAttr "orangeSphereLayer.nic" "sphereCollection1_shadingEngines.pic";
connectAttr "shaderOverride1.msg" "sphereCollection1_shadingEngines.cl";
connectAttr "shaderOverride1.msg" "sphereCollection1_shadingEngines.ch";
connectAttr "sphereCollection1Selector.out" "sphereCollection1_shadingEnginesSelector.in"
		;
connectAttr "groundCollection1Selector.c" "groundCollection1.sel";
connectAttr "sphereCollection1.nxt" "groundCollection1.prv";
connectAttr "orangeSphereLayer.lit" "groundCollection1.pls";
connectAttr "orangeSphereLayer.nic" "groundCollection1.pic";
connectAttr "cameraCollection1Selector.c" "cameraCollection1.sel";
connectAttr "groundCollection1.nxt" "cameraCollection1.prv";
connectAttr "orangeSphereLayer.lit" "cameraCollection1.pls";
connectAttr "orangeSphereLayer.nic" "cameraCollection1.pic";
connectAttr "lightCollection1Selector.c" "lightCollection1.sel";
connectAttr "cameraCollection1.nxt" "lightCollection1.prv";
connectAttr "orangeSphereLayer.lit" "lightCollection1.pls";
connectAttr "orangeSphereLayer.nic" "lightCollection1.pic";
connectAttr "_untitled_Selector.c" "_untitled_.sel";
connectAttr "orangeSphereLayer.lit" "_untitled_.pls";
connectAttr "orangeSphereLayer.nic" "_untitled_.pic";
connectAttr "_untitled_1Selector.c" "_untitled_1.sel";
connectAttr "purpleSphereLayer.lit" "_untitled_1.pls";
connectAttr "purpleSphereLayer.nic" "_untitled_1.pic";
connectAttr "whiteMaterialSG.pa" ":renderPartition.st" -na;
connectAttr "purpleMaterial.msg" ":defaultShaderList1.s" -na;
connectAttr "orangeMaterial.msg" ":defaultShaderList1.s" -na;
connectAttr "whiteMaterial.msg" ":defaultShaderList1.s" -na;
connectAttr "place2dTexture1.msg" ":defaultRenderUtilityList1.u" -na;
connectAttr "defaultRenderLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "rs_purpleSphereLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "rs_orangeSphereLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "spotLightShape.ltd" ":lightList1.l" -na;
connectAttr "purpleCheckerTexture.msg" ":defaultTextureList1.tx" -na;
connectAttr "orangeCheckerTexture.msg" ":defaultTextureList1.tx" -na;
connectAttr "movingSphereShape.iog" ":initialShadingGroup.dsm" -na;
connectAttr "purpleMaterial.msg" ":initialMaterialInfo.m";
connectAttr "purpleCheckerTexture.msg" ":initialMaterialInfo.t" -na;
connectAttr "spotLight.iog" ":defaultLightSet.dsm" -na;
// End of test.ma
