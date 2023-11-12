package TPSUP::FIX;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  parse_fix_message
  map_fixtag_by_name
  map_fixname_by_tag
  map_desc_by_tag_value
  get_fixname_by_tag
  get_fixtag_by_name
  get_fixtags_by_names
  get_desc_by_tag_value
  dump_v_by_k
  dump_fix_message
  dump_nested_fix_hash
  filter_fix
  csv_to_fix
  hash_to_fix
  diff_fix
  get_order_hierarchy
);

use Carp;
use Data::Dumper;
use TPSUP::UTIL qw(get_items
  unique_array sort_unique compile_paired_strings);
use TPSUP::FILE qw(get_in_fh get_out_fh
);

use TPSUP::CSV qw(query_csv2 print_csv_hashArray);

my $fixname_by_tag;
my $fixtag_by_name;

sub map_fixtag {
   my ($opt) = @_;

   return if $fixname_by_tag;

   #http://www.onixs.biz/fix-dictionary/4.2/fields_by_tag.html
   #http://www.onixs.biz/fix-dictionary/4.4/fields_by_tag.html
   my $standard_map = <<END;
      1 Account
      2 AdvId
      3 AdvRefID
      4 AdvSide
      5 AdvTransType
      6 AvgPx
      7 BeginSeqNo
      8 BeginString
      9 BodyLength
      10 CheckSum
      11 ClOrdID
      12 Commission
      13 CommType
      14 CumQty
      15 Currency
      16 EndSeqNo
      17 ExecID
      18 ExecInst
      19 ExecRefID
      20 ExecTransType
      21 HandlInst
      22 SecurityIDSource
      23 IOIID
      24 IOIOthSvc (no longer used)
      25 IOIQltyInd
      26 IOIRefID
      27 IOIQty
      28 IOITransType
      29 LastCapacity
      30 LastMkt
      31 LastPx
      32 LastQty
      33 NoLinesOfText
      34 MsgSeqNum
      35 MsgType
      36 NewSeqNo
      37 OrderID
      38 OrderQty
      39 OrdStatus
      40 OrdType
      41 OrigClOrdID
      42 OrigTime
      43 PossDupFlag
      44 Price
      45 RefSeqNum
      46 RelatdSym (no longer used)
      47 Rule80A(No Longer Used)
      48 SecurityID
      49 SenderCompID
      50 SenderSubID
      51 SendingDate (no longer used)
      52 SendingTime
      53 Quantity
      54 Side
      55 Symbol
      56 TargetCompID
      57 TargetSubID
      58 Text
      59 TimeInForce
      60 TransactTime
      61 Urgency
      62 ValidUntilTime
      63 SettlType
      64 SettlDate
      65 SymbolSfx
      66 ListID
      67 ListSeqNo
      68 TotNoOrders
      69 ListExecInst
      70 AllocID
      71 AllocTransType
      72 RefAllocID
      73 NoOrders
      74 AvgPxPrecision
      75 TradeDate
      76 ExecBroker
      77 PositionEffect
      78 NoAllocs
      79 AllocAccount
      80 AllocQty
      81 ProcessCode
      82 NoRpts
      83 RptSeq
      84 CxlQty
      85 NoDlvyInst
      86 DlvyInst
      87 AllocStatus
      88 AllocRejCode
      89 Signature
      90 SecureDataLen
      91 SecureData
      92 BrokerOfCredit
      93 SignatureLength
      94 EmailType
      95 RawDataLength
      96 RawData
      97 PossResend
      98 EncryptMethod
      99 StopPx
      100 ExDestination
      102 CxlRejReason
      103 OrdRejReason
      104 IOIQualifier
      105 WaveNo
      106 Issuer
      107 SecurityDesc
      108 HeartBtInt
      109 ClientID
      110 MinQty
      111 MaxFloor
      112 TestReqID
      113 ReportToExch
      114 LocateReqd
      115 OnBehalfOfCompID
      116 OnBehalfOfSubID
      117 QuoteID
      118 NetMoney
      119 SettlCurrAmt
      120 SettlCurrency
      121 ForexReq
      122 OrigSendingTime
      123 GapFillFlag
      124 NoExecs
      125 CxlType
      126 ExpireTime
      127 DKReason
      128 DeliverToCompID
      129 DeliverToSubID
      130 IOINaturalFlag
      131 QuoteReqID
      132 BidPx
      133 OfferPx
      134 BidSize
      135 OfferSize
      136 NoMiscFees
      137 MiscFeeAmt
      138 MiscFeeCurr
      139 MiscFeeType
      140 PrevClosePx
      141 ResetSeqNumFlag
      142 SenderLocationID
      143 TargetLocationID
      144 OnBehalfOfLocationID
      145 DeliverToLocationID
      146 NoRelatedSym
      147 Subject
      148 Headline
      149 URLLink
      150 ExecType
      151 LeavesQty
      152 CashOrderQty
      153 AllocAvgPx
      154 AllocNetMoney
      155 SettlCurrFxRate
      156 SettlCurrFxRateCalc
      157 NumDaysInterest
      158 AccruedInterestRate
      159 AccruedInterestAmt
      160 SettlInstMode
      161 AllocText
      162 SettlInstID
      163 SettlInstTransType
      164 EmailThreadID
      165 SettlInstSource
      166 SettlLocation
      167 SecurityType
      168 EffectiveTime
      169 StandInstDbType
      170 StandInstDbName
      171 StandInstDbID
      172 SettlDeliveryType
      173 SettlDepositoryCode
      174 SettlBrkrCode
      175 SettlInstCode
      176 SecuritySettlAgentName
      177 SecuritySettlAgentCode
      178 SecuritySettlAgentAcctNum
      179 SecuritySettlAgentAcctName
      180 SecuritySettlAgentContactName
      181 SecuritySettlAgentContactPhone
      182 CashSettlAgentName
      183 CashSettlAgentCode
      184 CashSettlAgentAcctNum
      185 CashSettlAgentAcctName
      186 CashSettlAgentContactName
      187 CashSettlAgentContactPhone
      188 BidSpotRate
      189 BidForwardPoints
      190 OfferSpotRate
      191 OfferForwardPoints
      192 OrderQty2
      193 SettlDate2
      194 LastSpotRate
      195 LastForwardPoints
      196 AllocLinkID
      197 AllocLinkType
      198 SecondaryOrderID
      199 NoIOIQualifiers
      200 MaturityMonthYear
      201 PutOrCall
      202 StrikePrice
      203 CoveredOrUncovered
      204 CustomerOrFirm
      205 MaturityDay
      206 OptAttribute
      207 SecurityExchange
      208 NotifyBrokerOfCredit
      209 AllocHandlInst
      210 MaxShow
      211 PegOffsetValue
      212 XmlDataLen
      213 XmlData
      214 SettlInstRefID
      215 NoRoutingIDs
      216 RoutingType
      217 RoutingID
      218 Spread
      219 Benchmark
      220 BenchmarkCurveCurrency
      221 BenchmarkCurveName
      222 BenchmarkCurvePoint
      223 CouponRate
      224 CouponPaymentDate
      225 IssueDate
      226 RepurchaseTerm
      227 RepurchaseRate
      228 Factor
      229 TradeOriginationDate
      230 ExDate
      231 ContractMultiplier
      232 NoStipulations
      233 StipulationType
      234 StipulationValue
      235 YieldType
      236 Yield
      237 TotalTakedown
      238 Concession
      239 RepoCollateralSecurityType
      240 RedemptionDate
      241 UnderlyingCouponPaymentDate
      242 UnderlyingIssueDate
      243 UnderlyingRepoCollateralSecurityType
      244 UnderlyingRepurchaseTerm
      245 UnderlyingRepurchaseRate
      246 UnderlyingFactor
      247 UnderlyingRedemptionDate
      248 LegCouponPaymentDate
      249 LegIssueDate
      250 LegRepoCollateralSecurityType
      251 LegRepurchaseTerm
      252 LegRepurchaseRate
      253 LegFactor
      254 LegRedemptionDate
      255 CreditRating
      256 UnderlyingCreditRating
      257 LegCreditRating
      258 TradedFlatSwitch
      259 BasisFeatureDate
      260 BasisFeaturePrice
      262 MDReqID
      263 SubscriptionRequestType
      264 MarketDepth
      265 MDUpdateType
      266 AggregatedBook
      267 NoMDEntryTypes
      268 NoMDEntries
      269 MDEntryType
      270 MDEntryPx
      271 MDEntrySize
      272 MDEntryDate
      273 MDEntryTime
      274 TickDirection
      275 MDMkt
      276 QuoteCondition
      277 TradeCondition
      278 MDEntryID
      279 MDUpdateAction
      280 MDEntryRefID
      281 MDReqRejReason
      282 MDEntryOriginator
      283 LocationID
      284 DeskID
      285 DeleteReason
      286 OpenCloseSettlFlag
      287 SellerDays
      288 MDEntryBuyer
      289 MDEntrySeller
      290 MDEntryPositionNo
      291 FinancialStatus
      292 CorporateAction
      293 DefBidSize
      294 DefOfferSize
      295 NoQuoteEntries
      296 NoQuoteSets
      297 QuoteStatus
      298 QuoteCancelType
      299 QuoteEntryID
      300 QuoteRejectReason
      301 QuoteResponseLevel
      302 QuoteSetID
      303 QuoteRequestType
      304 TotNoQuoteEntries
      305 UnderlyingSecurityIDSource
      306 UnderlyingIssuer
      307 UnderlyingSecurityDesc
      308 UnderlyingSecurityExchange
      309 UnderlyingSecurityID
      310 UnderlyingSecurityType
      311 UnderlyingSymbol
      312 UnderlyingSymbolSfx
      313 UnderlyingMaturityMonthYear
      314 UnderlyingMaturityDay
      315 UnderlyingPutOrCall
      316 UnderlyingStrikePrice
      317 UnderlyingOptAttribute
      318 UnderlyingCurrency
      319 RatioQty
      320 SecurityReqID
      321 SecurityRequestType
      322 SecurityResponseID
      323 SecurityResponseType
      324 SecurityStatusReqID
      325 UnsolicitedIndicator
      326 SecurityTradingStatus
      327 HaltReason
      328 InViewOfCommon
      329 DueToRelated
      330 BuyVolume
      331 SellVolume
      332 HighPx
      333 LowPx
      334 Adjustment
      335 TradSesReqID
      336 TradingSessionID
      337 ContraTrader
      338 TradSesMethod
      339 TradSesMode
      340 TradSesStatus
      341 TradSesStartTime
      342 TradSesOpenTime
      343 TradSesPreCloseTime
      344 TradSesCloseTime
      345 TradSesEndTime
      346 NumberOfOrders
      347 MessageEncoding
      348 EncodedIssuerLen
      349 EncodedIssuer
      350 EncodedSecurityDescLen
      351 EncodedSecurityDesc
      352 EncodedListExecInstLen
      353 EncodedListExecInst
      354 EncodedTextLen
      355 EncodedText
      356 EncodedSubjectLen
      357 EncodedSubject
      358 EncodedHeadlineLen
      359 EncodedHeadline
      360 EncodedAllocTextLen
      361 EncodedAllocText
      362 EncodedUnderlyingIssuerLen
      363 EncodedUnderlyingIssuer
      364 EncodedUnderlyingSecurityDescLen
      365 EncodedUnderlyingSecurityDesc
      366 AllocPrice
      367 QuoteSetValidUntilTime
      368 QuoteEntryRejectReason
      369 LastMsgSeqNumProcessed
      370 OnBehalfOfSendingTime
      371 RefTagID
      372 RefMsgType
      373 SessionRejectReason
      374 BidRequestTransType
      375 ContraBroker
      376 ComplianceID
      377 SolicitedFlag
      378 ExecRestatementReason
      379 BusinessRejectRefID
      380 BusinessRejectReason
      381 GrossTradeAmt
      382 NoContraBrokers
      383 MaxMessageSize
      384 NoMsgTypes
      385 MsgDirection
      386 NoTradingSessions
      387 TotalVolumeTraded
      388 DiscretionInst
      389 DiscretionOffsetValue
      390 BidID
      391 ClientBidID
      392 ListName
      393 TotNoRelatedSym
      394 BidType
      395 NumTickets
      396 SideValue1
      397 SideValue2
      398 NoBidDescriptors
      399 BidDescriptorType
      400 BidDescriptor
      401 SideValueInd
      402 LiquidityPctLow
      403 LiquidityPctHigh
      404 LiquidityValue
      405 EFPTrackingError
      406 FairValue
      407 OutsideIndexPct
      408 ValueOfFutures
      409 LiquidityIndType
      410 WtAverageLiquidity
      411 ExchangeForPhysical
      412 OutMainCntryUIndex
      413 CrossPercent
      414 ProgRptReqs
      415 ProgPeriodInterval
      416 IncTaxInd
      417 NumBidders
      418 BidTradeType
      419 BasisPxType
      420 NoBidComponents
      421 Country
      422 TotNoStrikes
      423 PriceType
      424 DayOrderQty
      425 DayCumQty
      426 DayAvgPx
      427 GTBookingInst
      428 NoStrikes
      429 ListStatusType
      430 NetGrossInd
      431 ListOrderStatus
      432 ExpireDate
      433 ListExecInstType
      434 CxlRejResponseTo
      435 UnderlyingCouponRate
      436 UnderlyingContractMultiplier
      437 ContraTradeQty
      438 ContraTradeTime
      439 ClearingFirm
      440 ClearingAccount
      441 LiquidityNumSecurities
      442 MultiLegReportingType
      443 StrikeTime
      444 ListStatusText
      445 EncodedListStatusTextLen
      446 EncodedListStatusText
      447 PartyIDSource
      448 PartyID
      449 TotalVolumeTradedDate
      450 TotalVolumeTradedTime
      451 NetChgPrevDay
      452 PartyRole
      453 NoPartyIDs
      454 NoSecurityAltID
      455 SecurityAltID
      456 SecurityAltIDSource
      457 NoUnderlyingSecurityAltID
      458 UnderlyingSecurityAltID
      459 UnderlyingSecurityAltIDSource
      460 Product
      461 CFICode
      462 UnderlyingProduct
      463 UnderlyingCFICode
      464 TestMessageIndicator
      465 QuantityType
      466 BookingRefID
      467 IndividualAllocID
      468 RoundingDirection
      469 RoundingModulus
      470 CountryOfIssue
      471 StateOrProvinceOfIssue
      472 LocaleOfIssue
      473 NoRegistDtls
      474 MailingDtls
      475 InvestorCountryOfResidence
      476 PaymentRef
      477 DistribPaymentMethod
      478 CashDistribCurr
      479 CommCurrency
      480 CancellationRights
      481 MoneyLaunderingStatus
      482 MailingInst
      483 TransBkdTime
      484 ExecPriceType
      485 ExecPriceAdjustment
      486 DateOfBirth
      487 TradeReportTransType
      488 CardHolderName
      489 CardNumber
      490 CardExpDate
      491 CardIssNum
      492 PaymentMethod
      493 RegistAcctType
      494 Designation
      495 TaxAdvantageType
      496 RegistRejReasonText
      497 FundRenewWaiv
      498 CashDistribAgentName
      499 CashDistribAgentCode
      500 CashDistribAgentAcctNumber
      501 CashDistribPayRef
      502 CashDistribAgentAcctName
      503 CardStartDate
      504 PaymentDate
      505 PaymentRemitterID
      506 RegistStatus
      507 RegistRejReasonCode
      508 RegistRefID
      509 RegistDtls
      510 NoDistribInsts
      511 RegistEmail
      512 DistribPercentage
      513 RegistID
      514 RegistTransType
      515 ExecValuationPoint
      516 OrderPercent
      517 OwnershipType
      518 NoContAmts
      519 ContAmtType
      520 ContAmtValue
      521 ContAmtCurr
      522 OwnerType
      523 PartySubID
      524 NestedPartyID
      525 NestedPartyIDSource
      526 SecondaryClOrdID
      527 SecondaryExecID
      528 OrderCapacity
      529 OrderRestrictions
      530 MassCancelRequestType
      531 MassCancelResponse
      532 MassCancelRejectReason
      533 TotalAffectedOrders
      534 NoAffectedOrders
      535 AffectedOrderID
      536 AffectedSecondaryOrderID
      537 QuoteType
      538 NestedPartyRole
      539 NoNestedPartyIDs
      540 TotalAccruedInterestAmt
      541 MaturityDate
      542 UnderlyingMaturityDate
      543 InstrRegistry
      544 CashMargin
      545 NestedPartySubID
      546 Scope
      547 MDImplicitDelete
      548 CrossID
      549 CrossType
      550 CrossPrioritization
      551 OrigCrossID
      552 NoSides
      553 Username
      554 Password
      555 NoLegs
      556 LegCurrency
      557 TotNoSecurityTypes
      558 NoSecurityTypes
      559 SecurityListRequestType
      560 SecurityRequestResult
      561 RoundLot
      562 MinTradeVol
      563 MultiLegRptTypeReq
      564 LegPositionEffect
      565 LegCoveredOrUncovered
      566 LegPrice
      567 TradSesStatusRejReason
      568 TradeRequestID
      569 TradeRequestType
      570 PreviouslyReported
      571 TradeReportID
      572 TradeReportRefID
      573 MatchStatus
      574 MatchType
      575 OddLot
      576 NoClearingInstructions
      577 ClearingInstruction
      578 TradeInputSource
      579 TradeInputDevice
      580 NoDates
      581 AccountType
      582 CustOrderCapacity
      583 ClOrdLinkID
      584 MassStatusReqID
      585 MassStatusReqType
      586 OrigOrdModTime
      587 LegSettlType
      588 LegSettlDate
      589 DayBookingInst
      590 BookingUnit
      591 PreallocMethod
      592 UnderlyingCountryOfIssue
      593 UnderlyingStateOrProvinceOfIssue
      594 UnderlyingLocaleOfIssue
      595 UnderlyingInstrRegistry
      596 LegCountryOfIssue
      597 LegStateOrProvinceOfIssue
      598 LegLocaleOfIssue
      599 LegInstrRegistry
      600 LegSymbol
      601 LegSymbolSfx
      602 LegSecurityID
      603 LegSecurityIDSource
      604 NoLegSecurityAltID
      605 LegSecurityAltID
      606 LegSecurityAltIDSource
      607 LegProduct
      608 LegCFICode
      609 LegSecurityType
      610 LegMaturityMonthYear
      611 LegMaturityDate
      612 LegStrikePrice
      613 LegOptAttribute
      614 LegContractMultiplier
      615 LegCouponRate
      616 LegSecurityExchange
      617 LegIssuer
      618 EncodedLegIssuerLen
      619 EncodedLegIssuer
      620 LegSecurityDesc
      621 EncodedLegSecurityDescLen
      622 EncodedLegSecurityDesc
      623 LegRatioQty
      624 LegSide
      625 TradingSessionSubID
      626 AllocType
      627 NoHops
      628 HopCompID
      629 HopSendingTime
      630 HopRefID
      631 MidPx
      632 BidYield
      633 MidYield
      634 OfferYield
      635 ClearingFeeIndicator
      636 WorkingIndicator
      637 LegLastPx
      638 PriorityIndicator
      639 PriceImprovement
      640 Price2
      641 LastForwardPoints2
      642 BidForwardPoints2
      643 OfferForwardPoints2
      644 RFQReqID
      645 MktBidPx
      646 MktOfferPx
      647 MinBidSize
      648 MinOfferSize
      649 QuoteStatusReqID
      650 LegalConfirm
      651 UnderlyingLastPx
      652 UnderlyingLastQty
      653 SecDefStatus
      654 LegRefID
      
END

   sub parse_map {
      my ($map_string) = @_;

      my @lines = split /\n/, $map_string;

      for my $line (@lines) {
         next if $line =~ /^\s*$/;

         if ( $line =~ /^\s*(\d+)\s+(\S+)/ ) {
            my ( $tag, $name ) = ( $1, $2 );

            $fixname_by_tag->{$tag} = $name;
            if ( $fixtag_by_name->{$name} ) {
               croak "name='$name' dupes in fix tag map";
            } else {
               $fixtag_by_name->{$name} = $tag;
            }
         } else {
            croak "bad format in fix tag map at line: $line";
         }
      }
   }

   parse_map($standard_map);
   parse_map( $opt->{FixMap} ) if $opt->{FixMap};
}

sub map_fixtag_by_name {
   my ($opt) = @_;
   map_fixtag($opt);
   return $fixtag_by_name;
}

sub map_fixname_by_tag {
   my ($opt) = @_;
   map_fixtag($opt);
   return $fixname_by_tag;
}

sub get_fixtag_by_name {
   my ( $name, $opt ) = @_;

   map_fixtag($opt);
   return $fixtag_by_name->{$name};
}

sub get_fixname_by_tag {
   my ( $tag, $opt ) = @_;

   map_fixtag($opt);
   return $fixname_by_tag->{$tag};
}

my $desc_by_tag_value;

sub map_desc_by_tag_value {
   my ($opt) = @_;

   return $desc_by_tag_value if $desc_by_tag_value;

   my $ref;

   #http://www.onixs.biz/fix-dictionary/4.2/fields_by_tag.html #Commission type

   $ref->{13} = <<END;
1 = per share
2 = percentage
3 = absolute
END

   #ExecInst
   $ref->{18} = <<END;
1 = Not held
2 = Work
3 = Go along
4 = Over the day
5 = Held
6 = Participate don't initiate
7 = Strict scale
8 = Try to scale
9 = Stay on bidside
0 = Stay on offerside
A = No cross (cross is forbidden)
B = OK to cross
C = Call first
D = Percent of volume
E = Do not increase - DNI
F = Do not reduce - DNR
G = All or none - AON
H = Reinstate on System Failure (mutually exclusive with Q)
I = Institutions only
J = Reinstate on Trading Halt (mutually exclusive with K)
K = Cancel on Trading Halt (mutually exclusive with L)
L = Last peg (last sale)
M = Mid-price peg (midprice of inside quote)
N = Non-negotiable
0 = Opening peg
P = Market peg
Q = Cancel on System Failure (mutually exclusive with H)
R = Primary peg (primary market - buy at bid/sell at offer)
S = Suspend
T = Fixed Peg to Local best bid or offer at time of order
U = Customer Display Instruction (RuleAc-/4) 
V = Netting (for Forex)
W = Peg to VWAP
X = Trade Along
Y = Try to Stop
Z = Cancel if Not Best
a = Trailing Stop Peg 
b = Strict Limit (No Price <44> Improvement)
c = Ignore Price <44> Validity Checks
d = Peg to Limit Price <44>
e = Work to Target Strategy
END

   #ExecTransType
   $ref->{20} = <<END;
0 = New
1 = Cancel
2 = Correct
3 = Status
END

   #HandlInst
   $ref->{21} = <<END;
1 = Automated execution order, private, no Broker intervention
2 = Automated execution order, public. Broker intervention OK
3 = Manual order, best execution
END

   #IDSource
   $ref->{22} = <<END;
1 = CUSIP
2 = SEDOL
3 = QUIK
4 = ISIN number
5 = RIC code
6 = ISO Currency <15> Code
7 = ISO Country <421> Code
8 = Exchange Symbol <55>
9 = Consolidated Tape Association (CTA) Symbol <55> (SIAC CTS/CQS line format) 
END

   #MsgType
   $ref->{35} = <<END;
0 = Heartbeat <0>
1 = Test Request <1>
2 = Resend Request <2>
3 = Reject <3>
4 = Sequence Reset <4>
5 = Logout <5>
6 = Indication of Interest <6>
7 = Advertisement <7>
8 = Execution Report <8>
9 = Order Cancel Reject <9>
A = Logon <A>
B = News <B>
C = Email <C>
D = Order - Single <D>
E = Order - List <E>
F = Order Cancel Request <F>
G = Order Cancel/Replace Request <G>
H = Order Status Request <H>
J = Allocation <J>
K = List Cancel Request <K>
L = List Execute <L>
M = List Status Request <M>
N = List Status <N>
P = Allocation ACK <P>
Q = Don't Know Trade <Q> (DK)
R = Quote Request <R>
S = Quote <S>
T = Settlement Instructions <T>
V = Market Data Request <V>
W = Market Data-Snapshot/Full Refresh
X = Market Data-Incremental Refresh
Y = Market Data Request Reject <Y>
Z = Quote Cancel <Z>
a = Quote Status Request <a>
b = Quote Acknowledgement <b>
c = Security Definition Request <c>
d = Security Definition <d>
e = Security Status Request <e>
f = Security Status <f>
g = Trading Session Status Request <g>
h = Trading Session Status <h>
i = Mass Quote <i>
j = Business Message Reject <j>
k = Bid Request <k>
l = Bid Response <1> (lowercase L)
m = List Strike Price <44>
n = XML message (e.g. non-FIX MsgType <35>)
o = Registration Instructions <o>
p = Registration Instructions Response <p>
q = Order Mass Cancel Request <q>
r = Order Mass Cancel Report <r>
s = New Order - Cross
t = Cross Order Cancel/Replace Request <t> (a.k.a. Cross Order Modification Request)
u = Cross Order Cancel Request <u>
v = Security Type Request <v>
w = Security Types <w>
x = Security List Request <x>
y = Security List <y>
z = Derivative Security List Request <z>
AA = Derivative Security List <AA>
AB = New Order - Multileg
AC = Multileg Order Cancel/Replace <AC> (a.k.a. Multileg Order Modification Request)
AD = Trade Capture Report Request <AD>
AE = Trade Capture Report <AE>
AF = Order Mass Status Request <AF>
AG = Quote Request Reject <AG>
AH = RFQ Request <AH>
AI = Quote Status Report <AI>
AJ = Quote Response <AJ>
AK = Confirmation <AK>
AL = Position Maintenance Request <AL>
AM = Position Maintenance Report <AM>
AN = Request For Positions <AN>
A0 = Request For Positions <AN> Ack
AP = Position Report <AP>
AQ = Trade Capture Report Request Ack <AQ>
AR = Trade Capture Report Ack <AR>
AS = Allocation Report <AS> (aka Allocation Claim)
AT = Allocation Report Ack <AT> (aka Allocation Claim Ack)
AU = Confirmation Ack <AU> (aka Affirmation)
AV = Settlement Instruction Request <AV>
AW = Assignment Report <AW>
AX = Collateral Request <AX>
AY = Collateral Assignment <AY>
AZ = Collateral Response <AZ>
BA = Collateral Report <BA>
BB = Collateral Inquiry <BB>
BC = Network (Counterparty System) Status Request
BD = Network (Counterparty System) Status Response
BE = User Request <BE>
BF = User Response <BF>
BG = Collateral Inquiry Ack <BG>
BH = Confirmation Request <BH>
END

   #OrdStatus
   $ref->{39} = <<END;
0 = New
1 = Partially filled
2 = Filled
3 = Done for day
4 = Canceled
5 = Replaced
6 = Pending Cancel (e.g. result of Order Cancel Request <F>) 7 = Stopped
8 = Rejected
9 = Suspended
A = Pending New
B = Calculated
C = Expired
D = Accepted for bidding
E = Pending Replace (e.g. result of Order Cancel/Replace Request <G>)
END

   #OrdType
   $ref->{40} = <<END;
1 = Market
2 = Limit
3 = Stop
4 = Stop limit
5 = Market on close
6 = With or without
7 = Limit or better
8 = Limit with or without
9 = On basis
A = On close
B = Limit on close
C =Forex - Market
D = Previously quoted
E = Previously indicated
F = Forex - Limit
G = Forex - Swap
H = Forex - Previously Quoted
I = Funari (Limit Day Order with unexecuted portion handled as Market On Close, e.g. Japan)
P = Pegged
END

   #PossDupFlag
   $ref->{43} = <<END;
Y = Possible duplicate
N = Original transmission
END

   #Rule8OA(aka OrderCapacity)
   $ref->{47} = <<END;
A = Agency single order
B = Short exempt transaction (refer to A type)
C = Program Order, non-index arb, for Member firm/org
D = Program Order, index arb, for Member firm/org
E = Registered Equity Market Maker trades
F = Short exempt transaction (refer to W type)
H = Short exempt transaction (refer to I type)
I = Individual Investor, single order
J = Program Order, index arb, for individual customer
K = Program Order, non-index arb, for individual customer
L = Short exempt transaction for member competing market-maker affiliated with the firm clearing the trade (refer to P and 0 types)
M = Program Order, index arb, for other member
N = Program Order, non-index arb, for other member
0 = Competing dealer trades
P = Principal
R = Competing dealer trades
S = Specialist trades
T = Competing dealer trades
U = Program Order, index arb, for other agency
W = All other orders as agent for other member
X = Short exempt transaction for member competing market-maker not affiliated with the firm clearing the trade (refer to W and T types)
Y = Program Order, non-index arb, for other agency
Z = Short exempt transaction for non-member competing market-maker (refer to A and R types)
END

   #Side
   $ref->{54} = <<END;
1 = Buy
2 = Sell
3 = Buy minus
4 = Sell plus
5 = Sell short
6 = Sell short exempt
7 = Undisclosed (valid for 101 <6> and List Order messages only)
8 = Cross (orders where counterparty is an exchange, valid for all messages except IOIs)
9 = Cross short
A = Cross short exempt
B = "As Defined" (for use with multileg instruments)
C = "Opposite" (for use with multileg instruments)
D = Subscribe (e.g. CIV)
E = Redeem (e.g. CIV)
F = Lend (FINANCING - identifies direction of collateral)
G = Borrow (FINANCING - identifies direction of collateral)
END

   #TimeInForce
   $ref->{59} = <<END;
0 = Day
1 = Good Till Cancel (GTC)
2 = At the Opening (OPG)
3 = Immediate or Cancel (IOC)
4 = Fill or Kill (FOK)
5 = Good Till Crossing (GTX)
6 = Good Till Date
END

   # OpenClose
   $ref->{77} = <<END;
O = Open
C = Close
R = Rolled
F = FIFO
END

   # ProcessCode
   $ref->{81} = <<END;
0 = regular
1 = soft dollar
2 = step-in
3 = step-out
4 = soft-dollar step-in
5 = soft-dollar step-out
6 = plan sponsor
END

   #ExecType
   $ref->{150} = <<END;
0 = New
1 = Partial fill
2 = Fill
3 = Done for day
4 = Canceled
5 = Replace
6 = Pending Cancel (result of 35=F)
7 = Stopped
8 = Rejected
9 = Suspended
A = Pending New
B = Calculated
C = Expired
D = Restated (ExecutionRpt sent unsolicited by sellside)
E = Pending Replace (result of 35=G)
F = Trade (partial fill or fill)
G = Trade Correct (formerly an ExecTransType)
H = Trade Cancel (formerly an ExecTransType)
I = Order Status (formerly an ExecTransType) 
END

   # CustomerOrFirm
   $ref->{204} = <<END;
0 = Customer
1 = Firm
END

   # LegPositionEffect
   $ref->{564} = <<END;
O = Open
C = Close
R = Rolled
F = FIFO
END

   # LegCFICode
   $ref->{608} = <<END;
OC = Option Call
OP = Option Put
END

   # LegSide
   $ref->{624} = <<END;
1 = Buy
2 = Sell
3 = Buy minus
4 = Sell plus
5 = Sell short
6 = Sell short exempt
7 = Undisclosed (valid for 101 and List Order messages only)
8 = Cross (orders where counterparty is an exchange, valid for all messages except IOIs)
9 = Cross short
END

   sub parse_ref {
      my ($o) = @_;

      for my $tag ( keys %$ref ) {
         my $rawmap = $ref->{$tag};

         my @lines = split /\n/, $rawmap;

         for my $line (@lines) {
            next if $line =~ /^\s*$/;

            if ( $line =~ /^\s*(\S+)\s*=\s*(\S.*)/ ) {
               my ( $value, $desc ) = ( $1, $2 );

               $desc =~ s/\s+$//;    # trim the ending spaces

               $desc_by_tag_value->{$tag}->{$value} = $desc;
            } else {
               croak
"bad format in source='$o->{source}' for tag '$tag' fix desc map at line: $line";
            }
         }
      }
   }

   parse_ref( { source => 'inside-module' } );

   return $desc_by_tag_value if !$opt->{FixDict};

   # user-supplied dictionary will complement of overwrite inside-module
   # dictionary (defined above)

   eval $opt->{FixDict};

   $opt->{verbose} && print "after adding user-supplied FixDict, ref = \n",
     Dumper($ref);

   parse_ref( { source => 'user-supplied' } );

   return $desc_by_tag_value;
}

sub get_desc_by_tag_value {
   my ( $tag, $value, $opt ) = @_;

   map_desc_by_tag_value($opt);

   return $desc_by_tag_value->{$tag}->{$value};
}

sub parse_fix_message {
   my ( $line, $opt ) = @_;

   return undef if !$line;

   chomp $line;

#TIME(05:39:37:015) EID(0) JMSID(ID:db_us_GTO_GEMS_S006PROD.35EB53D568E41950096:11763) LEN(196) RAW_DATA(8=FIX.4.1^A9=0172^A35=D^A34=1491...^A59=0^A100=0^A10=142^A)
   $line =~ s/.*\b(8=FIX[.].*)/$1/;
   $line =~ s/['")
]+$//;

#TIME(13:15:10:190) EID(0) JMSID(ID:db_us_GTO_GEMS_S008UAT.651955D5929412A205:10) LEN(626) RAW_DATA(35=8^A49=pti^A50=NYI^A56=AXIOM^A57=AXIOM...^A10011=gems.ny.reportrouter.in^A)

   my $delimiter;

   if ( $opt->{FixDelimiter} ) {
      $delimiter = $opt->{FixDelimiter};
   } else {
      if (  $line =~ /\b8=FIX[.0-9]+?([^.0-9]+)[0-9]/
         || $line =~ /\b35=[0-9A-Z]{1,2}([^.0-9A-Z]+)[0-9]+=/ )
      {
         $delimiter = $1;
         if ( $delimiter eq '^A' ) {

           # the delmiter is caret+A because of copy-paste, we need to
           # convert caret+A to control-A in order to make the later split work.
           # otherwise, caret+A means 'not A' in split.
            $line =~ s/^A//g;
            $delimiter = '';
            $opt->{verbose}
              && print "converted delimiter from '^A' (^+A) to '' (Ctrl+A)\n";
         }
      } elsif ( $line =~ /^\s*\d+=[^=]+$/ ) {

         # only one element, eg, 35=D, or 40=1
         $delimiter = 'not_needed';
      } else {
         $opt->{verbose} && warn "cannot figure out fix delimiter: $line";
         return undef;
      }
   }

   if ( $opt->{verbose} ) {
      print STDERR "delimiter is '$delimiter'\n";
   }

   my $delimiter_pattern;
   if ( "$delimiter" eq "|" ) {
      $delimiter_pattern = "[$delimiter]";
   } elsif ( "$delimiter" eq '^' || "$delimiter" eq '$' || "$delimiter" eq '?' )
   {
      $delimiter_pattern = "\\$delimiter";
   } else {
      $delimiter_pattern = "$delimiter";
   }

   my $NestedFix = $opt->{NestedFix};
   my $is_New_Multileg
     ;    # http://www.onixs.biz/fix-dictionary/4.4/msgType_AB_6566.html
   my $is_New_List;  # http://www.onixs.biz/fix-dictionary/4.4/msgType_E_69.html

   my $v_by_k;
   my $num_components = 0;
   my $in_block;
   my $comp_idx = 0;
   my $last_tag;
   my $common_by_k;
   my @common_tag_order;

   my $components;    # array of hashes.
   my $CompTagMatrix;

   my $eq_qr = qr/=/;
   my $k_qr  = qr/^.+[^0-9A-Za-z._-]/;

   for my $pair ( split /$delimiter_pattern/, $line ) {

      #next if $pair !~ /=/;
      next if $pair !~ /$eq_qr/;

      #my ($k, $v) = split /=/, $pair;
      my ( $k, $v ) = split /$eq_qr/, $pair;

      next if !defined $k || "$k" eq "";

      # forgot about what this is for
      # $k =~ s/^.+[^0-9A-Za-z._-]//;
      $k =~ s/$k_qr//;

      next if !defined $k || !defined $v || "$k" eq "" || "$v" eq "";

      next if $opt->{OnlyNumeric} && "$k" !~ /^\d+$/;

      if ( "$k" eq "35" ) {
         if ( $v eq 'AB' ) {
            $is_New_Multileg = 1;
         } elsif ( $v eq 'E' ) {
            $is_New_List = 1;
         }
      }

      if ($NestedFix) {
         if ( !$in_block ) {
            if ( $is_New_Multileg && "$k" eq "555" ) {
               $num_components = $v;

               if ($v) {
                  $in_block++;
               }    # otherwise when 555=0, no leg block

               #tag 555 belongs to common section
               $common_by_k->{$k} = $v;
               push @common_tag_order, $k;
            } elsif ( $is_New_List && "$k" eq "11" ) {
               $in_block++;

               #tag 11 belongs to component section
               push @{ $CompTagMatrix->[$comp_idx] }, $k;
               $components->[$comp_idx]->{$k} = $v;
            } else {
               $common_by_k->{$k} = $v;
               push @common_tag_order, $k;
            }
         } else {

            # now we are $in_block

            if ($is_New_Multileg) {

               # http://www.onixs.biz/fix-dictionary/4.4/msgType_AB_6566.html
               # leg block ending with this four tags
               #=> 654 LegRefID N
               #=> 566 LegPrice N
               #=> 587 LegSettlType N
               #=> 588 LegSettlDate N

               if (
                     "$k" ne "654"
                  && "$k" ne "566"
                  && "$k" ne "587"
                  && "$k" ne "588"
                  && (  !$last_tag
                     || "$last_tag" eq "654"
                     || "$last_tag" eq "566"
                     || "$last_tag" eq "587"
                     || "$last_tag" eq "588" )
                 )
               {
                  # we have just completed a leg, start a new one
                  $comp_idx++;

                  if ( $comp_idx >= $num_components ) {

                  # we finished the whole leg block and are back to common tags,
                     $in_block = 0;

                     $common_by_k->{$k} = $v;
                     push @common_tag_order, $k;
                  } else {

                     # this is the next leg

                     push @{ $CompTagMatrix->[$comp_idx] }, $k;
                     $components->[$comp_idx]->{$k} = $v;
                  }
               } else {

                  # we are still within the current leg
                  {
                     push @{ $CompTagMatrix->[$comp_idx] }, $k;
                     $components->[$comp_idx]->{$k} = $v;
                  }
               }
            } elsif ($is_New_List) {

               # http://www.onixs.biz/fix-dictionary/4.4/msgType_E_69.html
               if ( "$k" eq "11" ) {

                  # starts a list
                  $comp_idx++;
               }

               push @{ $CompTagMatrix->[$comp_idx] }, $k;
               $components->[$comp_idx]->{$k} = $v;
            }
         }
      } else {

         # not assuming Nested FIX, very naive
         $v_by_k->{$k} = $v;
      }

      if ( "$k" eq "10" ) {
         $common_by_k->{$k} = $v;
         last;
      }

      $last_tag = $k;
   }

   if ( $opt->{NestedFix} ) {
      if ( $opt->{ReturnNestedInArray} ) {
         my $ret;

         if ($components) {
            for my $leg (@$components) {
               my $r;
               %{$r} = ( %$common_by_k, %$leg );

               push @$ret, $r;
            }
         } else {
            push @$ret, $common_by_k;
         }

         return $ret;
      } else {
         my $ret;
         $ret->{common}     = $common_by_k;
         $ret->{CommTags}   = \@common_tag_order;
         $ret->{components} = $components;
         $ret->{CompTagMx}  = $CompTagMatrix;
         $ret->{Delimiter}  = $delimiter;

         return $ret;
      }
   } else {

      # not assuming Nested FIX, very naive
      return $v_by_k;
   }
}

sub dump_v_by_k {
   my ( $v_by_k, $opt ) = @_;

   my $DumpFH = $opt->{DumpFH} ? $opt->{DumpFH} : \*STDERR;

   $opt->{verbose} && print {$DumpFH} "dump_v_by_k() v_by_k= \n",
     Dumper($v_by_k);

   my $need_tag;

   if ( $opt->{tags} ) {
      for my $tag ( split /,/, $opt->{tags} ) {
         $need_tag->{$tag}++;
      }
   }

   for my $k ( sort { $a <=> $b } ( keys %$v_by_k ) ) {
      if ( !$need_tag || $need_tag->{$k} ) {
         my $values;

         my $v = $v_by_k->{$k};

         my $fixname = get_fixname_by_tag($k);
         $fixname = '' if !defined $fixname;
         my $left = sprintf( "%s %3d", $fixname, $k );

         my $right = $v;

         my $desc = get_desc_by_tag_value( $k, $v );

         if ( defined $desc ) {
            $right .= " ($desc)";
         }

         printf {$DumpFH} "%25s =%s\n", $left, "$right";
      }
   }
}

sub dump_fix_message {
   my ( $message, $opt ) = @_;

   my $DumpFH = defined( $opt->{DumpFH} ) ? $opt->{DumpFH} : \*STDERR;

   my $ref = parse_fix_message( $message, $opt );

   if ( $opt->{NestedFix} ) {
      dump_nested_fix_hash( $ref, $opt );
   } elsif ( $ref->{35} eq "AB" || $ref->{35} eq "E" ) {

      # force to parse as NestedFix
      $ref = parse_fix_message( $message, { %$opt, NestedFix => 1 } );

      dump_nested_fix_hash( $ref, $opt );
   } else {
      dump_v_by_k( $ref, {%$opt} );
   }
}

sub dump_nested_fix_hash {
   my ( $ref, $opt ) = @_;

   my $DumpFH = defined( $opt->{DumpFH} ) ? $opt->{DumpFH} : \*STDERR;

   $opt->{verbose} && print {$DumpFH} "dump_nested_fix_hash() ref= \n",
     Dumper($ref);

   dump_v_by_k( $ref->{common}, $opt );

   print {$DumpFH} "----- begin components -----\n";

   for my $component ( @{ $ref->{components} } ) {
      print {$DumpFH} "\n";
      dump_v_by_k( $component, $opt );
   }

   print {$DumpFH} "\n";
   print {$DumpFH} "----- end components -----\n";
}

sub get_fixtags_by_names {
   my ( $names, $opt ) = @_;

   my @out_array;

   for my $name (@$names) {
      my $tag = get_fixtag_by_name( $name, $opt );

      $tag = $name if !defined $tag;

      push @out_array, $tag;
   }

   return \@out_array;
}

sub get_order_hierarchy {
   my ( $file, $opt ) = @_;

   my $pick_this_ord;

   if ( $opt->{FixPickOrdFile} ) {
      $pick_this_ord = get_items(
         $opt->{FixPickOrdFile},
         {
            InlineDelimiter => $opt->{FixPickOrdDelimiter},
            ReturnHashCount => 1,
         }
      );

      $opt->{verbose} && print STDERR "pick_this_ord = ",
        Dumper($pick_this_ord);
   }

   my $in_fh = get_in_fh( $file, $opt );

   croak "cannot open $file" if !$in_fh;

   my $line_count = 0;
   my $last_progress_time;
   my $begin_progress_time;

   if ( $opt->{ShowProgress} ) {
      $begin_progress_time = time();
      $last_progress_time  = $begin_progress_time;
   }

   my $exists_ord;

   my $ord_by_orig;

   while (<$in_fh>) {
      my $line = $_;
      chomp $line;

      $line_count++;

      if ( $opt->{ShowProgress} ) {
         if ( $line_count % $opt->{ShowProgress} == 0 ) {
            my $now = time();

            my $seconds = $now - $last_progress_time;

            print STDERR
"$line_count lines are processed. $opt->{ShowProgress} lines in $seconds seconds\n";
            $last_progress_time = $now;
         }
      }

      next if $line !~ /11=/;

      my $parsed =
        parse_fix_message( $line, { %$opt, ReturnNestedInArray => 1 } );

      my @splits;
      if ( $opt->{NestedFix} ) {
         @splits = @{$parsed};
      } else {
         @splits = ($parsed);    #treat non-leg message as single leg
      }

      for my $s (@splits) {
         my $ord  = $s->{11};
         my $orig = $s->{41};
         if ( defined($ord) && "$ord" ne "" ) {
            $exists_ord->{$ord}++;
         } else {
            next;
         }

         if ( defined($orig) && "$orig" ne "" ) {
            $ord_by_orig->{$orig} = $ord;
         }
      }
   }

   if ( $opt->{ShowProgress} ) {
      my $now = time();

      my $total_sec = $now - $begin_progress_time;

      print STDERR
        "Total $line_count lines are processed in $total_sec seconds.\n";
   }

   $opt->{verbose} && print STDERR "exists_ord = ",  Dumper($exists_ord);
   $opt->{verbose} && print STDERR "ord_by_orig = ", Dumper($ord_by_orig);

   my $chain_by_ord;

   for my $id ( keys %$exists_ord ) {
      @{ $chain_by_ord->{$id} } = ();

      my $current = $id;

      while ( exists $ord_by_orig->{$current} ) {
         my $child = $ord_by_orig->{$current};

         delete $ord_by_orig->{$current}
           ;    # delete the link to ensure we only use it once

         push @{ $chain_by_ord->{$id} }, $child;

         last if $current eq $child;    # sometimes tag 11 and 41 are equal

         if ( exists $chain_by_ord->{$child} ) {

            # now child has a chain, so we append it to the parent chain
            push @{ $chain_by_ord->{$id} }, @{ $chain_by_ord->{$child} };

            # remove the child chain and free memory
            @{ $chain_by_ord->{$child} } = ();
            delete $chain_by_ord->{$child};

            last;
         }

         $current = $child;
      }
   }

   $opt->{verbose} && print STDERR "chain_by_ord = ", Dumper($chain_by_ord);

   my @array;

   for my $id ( keys %$chain_by_ord ) {
      if ( $opt->{FixPickOrdFile} ) {
         my $matched;

         for my $j ( ( $id, @{ $chain_by_ord->{$id} } ) ) {
            if ( $pick_this_ord->{$j} ) {
               $matched++;
               last;
            }
         }

         next if !$matched;
      }

      my $ref;

      $ref->{OrigClOrdID} = $id;
      $ref->{ClOrdIDs}    = join( " ", @{ $chain_by_ord->{$id} } );

      push @array, $ref;
   }

   my $ret;
   $ret->{array}   = \@array;
   $ret->{columns} = [qw(OrigClOrdID ClOrdIDs)];

   if ( $opt->{FixHierArchyOutput} ) {
      print_csv_hashArray(
         $ret->{array},
         $ret->{columns},
         {
            %$opt,
            RenderStdout => $opt->{RenderOutput},
            output       => $opt->{FixHierArchyOutput},
         }
      );
   }

   return $ret;
}

sub filter_fix {
   my ( $file, $opt ) = @_;

   my $fixopt;

   if ($opt) {
      $fixopt = { %$opt, FIX => 1 };
   } else {
      $fixopt = { FIX => 1 };
   }

   my $NestedFix = $opt->{NestedFix};

   my $in_fh = get_in_fh( $file, $opt ) or croak "cannot open $file";

   # {FixFilterTag} and {FixFilterFile}/$opt->{FixFilterArray} is a way
   # to quicky filter in lines based on one tag. it is to achieve this
   # sql-equivallent: $tag(49) in ('A', 'B', 'C', ...)

   my @FilterTags;
   my $FilterExists;

   if ( $opt->{FixFilterTag} ) {
      @FilterTags = split /,/, $opt->{FixFilterTag};

      if ( $opt->{FixFilterFile} ) {
         $FilterExists = get_items_from_file(
            $opt->{FixFilterFile},
            {
               InlineDelimiter => $opt->{FixFilterDelimiter},
               ReturnHashCount => 1,
            }
         );
      } elsif ( $opt->{FixFilterArray} ) {
         for my $v ( @{ $opt->{FixFilterArray} } ) {
            $FilterExists->{$v}++;
         }
      } elsif ( $opt->{FixFilterHash} ) {
         $FilterExists = $opt->{FixFilterHash};
      }
   }

   my $matchExps;
   if ( $opt->{MatchExps} && @{ $opt->{MatchExps} } ) {
      @$matchExps = map { TPSUP::Expression::compile_exp( $_, $fixopt ) }
        @{ $opt->{MatchExps} };
   }

   my $excludeExps;
   if ( $opt->{ExcludeExps} && @{ $opt->{ExcludeExps} } ) {
      @$excludeExps = map { TPSUP::Expression::compile_exp( $_, $fixopt ) }
        @{ $opt->{ExcludeExps} };
   }

   my $Exps;
   my $Cols;

   my $expcfg;

   for my $attr (qw(TempExps ExportExps)) {
      if ( $opt->{$attr} ) {
         $expcfg->{$attr} = compile_paired_strings( $opt->{$attr}, $fixopt );
      }
   }

   my $exportExps = $expcfg->{ExportExps}->{Exps};
   my @exportTags =
     $expcfg->{ExportExps}->{Cols} ? @{ $expcfg->{ExportExps}->{Cols} } : ();

   my $tempExps = $expcfg->{TempExps}->{Exps};
   my @tempTags =
     $expcfg->{TempExps}->{Cols} ? @{ $expcfg->{TempExps}->{Cols} } : ();

   my @SelectTags;
   if ( $opt->{SelectTags} ) {
      @SelectTags = split /,/, $opt->{SelectTags};
   }

   # $ perl -e 'my @a=(); my @b=(); my @c=(@a,@b); print scalar(@c), "\n";'
   # 0
   # $ perl -e 'my @a=(); my @b=(3,4); my @c=(@a,@b); print scalar(@c), "\n";'
   # 2
   my @OutColumns = ( @SelectTags, @exportTags );

   my $OutDelimiter = $opt->{OutDelimiter} ? $opt->{OutDelimiter} : ',';

   # for csv output
   my $out_fh;
   my $PrintCsv;

   if ( $opt->{Output} ) {

      # four different formats, but only support one at a time
      # 1. massaged fix message if $opt->{GenFixMsg}
      # 2. original log line if $opt->{FIXPrintLog}
      # 3. rendered csv output if $opt->{PxenderOutput}
      # 4. else, non-rendered csv output

      if ( !$opt->{GenFixMsg} && !$opt->{FIXPrintLog} ) {
         $PrintCsv = 1;
      }

      $out_fh = get_out_fh( $opt->{Output}, $opt );

      croak "cannot write to $opt->{Output}" if !$out_fh;
   }

   my $ret;     #return
   my $ref1;    #temp StructuredHash

   my $match_count = 0;
   my $OrderInfo;
   my $seen_tag;

   my $line_count = 0;
   my $last_progress_time;
   my $begin_progress_time;

   if ( $opt->{ShowProgress} ) {
      $begin_progress_time = time();
      $last_progress_time  = $begin_progress_time;
   }

   # convert static patterns to qr; this will speed up matching
   # http://forums.devshed.com/perl-programming-6/qr-vs-regex-223400.html
   my @Exclude_qrs;
   if ( $opt->{ExcludePatterns} ) {
      for my $p ( @{ $opt->{ExcludePatterns} } ) {
         push @Exclude_qrs, qr/$p/;
      }
   }

   my @Match_qrs;
   if ( $opt->{MatchPatterns} ) {
      for my $p ( @{ $opt->{MatchPatterns} } ) {
         push @Match_qrs, qr/$p/;
      }
   }

   my $NewOrder_qr = qr/35=[ADEGF]/;

   while (<$in_fh>) {
      my $line = $_;
      chomp $line;

      $line_count++;

      if ( $opt->{ShowProgress} ) {
         if ( $line_count % $opt->{ShowProgress} == 0 ) {
            my $now = time();

            my $seconds = $now - $last_progress_time;

            print STDERR
"$line_count lines are processed. $opt->{ShowProgress} lines in $seconds seconds\n";

            $last_progress_time = $now;
         }
      }

      if ( $opt->{SourceNewOrder} ) {
         if ( $line =~ /$NewOrder_qr/ ) {
            my $parsed =
              parse_fix_message( $line, { %$opt, ReturnNestedInArray => 1 } );

            my @splits;
            if ( $opt->{NestedFix} ) {
               @splits = @{$parsed};
            } else {
               @splits = ($parsed);    #treat non-leg message as single leg
            }

            for my $r (@splits) {
               my $tag35 = $r->{35};
               my $OrdID = $r->{11};

               next if !defined($tag35) || !defined($OrdID);

               if ( $tag35 eq 'D' ) {

                  # this is an order entry

                  $OrderInfo->{$OrdID} = $r;
               } elsif ( $tag35 eq 'G' ) {

                  # this is an order replace

                  my $old_OrdID = $r->{41};

                  if (  defined($old_OrdID)
                     && defined( $OrderInfo->{$old_OrdID} ) )
                  {
                     %{ $OrderInfo->{$OrdID} } =
                       ( %{ $OrderInfo->{$old_OrdID} }, %$r );
                  }
               } elsif ( $tag35 eq 'F' ) {

                  # this is an order cancel

                  my $old_OrdID = $r->{41};

                  if (  defined($old_OrdID)
                     && defined( $OrderInfo->{$old_OrdID} ) )
                  {
                     %{ $OrderInfo->{$OrdID} } =
                       ( %{ $OrderInfo->{$old_OrdID} }, { 11 => $OrdID } );
                  }
               } elsif ( $tag35 eq 'AB' ) {

                  # this is a new Multileg order

                  my $LegID = $r->{654};

                  if ( defined($LegID) ) {
                     $OrderInfo->{$OrdID}->{$LegID} = $r;
                  } else {
                     carp
"New Multileg order: 35=$tag35,11=$OrdID,has no leg (tag 654)";
                     dump_fix_message($line);
                  }
               } elsif ( $tag35 eq 'AC' ) {

                  # this is a Multileg replace

                  # Multileg order replace can only replace common tags, not
                  # component tags
                  # http://www.onixs.biz/fix-dictionary/4.4/msgType_AC_6567.html

                  my $old_OrdID = $r->{41};

                  if (  defined($old_OrdID)
                     && defined( $OrderInfo->{$old_OrdID} ) )
                  {
                     for my $LegID ( keys %{ $OrderInfo->{$old_OrdID} } ) {
                        %{ $OrderInfo->{$OrdID}->{$LegID} } =
                          ( %{ $OrderInfo->{$old_OrdID}->{$LegID} }, %$r );
                     }
                  } else {
                     carp
"Multileg replace: 35=$tag35,11=$OrdID,41='$old_OrdID'. cannot find old order by tag 41";
                     dump_fix_message($line);
                  }
               } elsif ( $tag35 eq 'E' ) {

                 # this is a new List. There is no replace for List, only Cancel

                  my $ListID = $r->{66};

                  if ( defined($ListID) ) {
                     $OrderInfo->{$ListID}->{$OrdID} = $r;
                  } else {
                     carp
"New List order: 35=$tag35,11=$OrdID,has no ListID (tag 66)";
                     dump_fix_message($line);
                  }
               }
            }
         }
      }

      if (@Exclude_qrs) {
         my $should_exclude = 1;

         for my $qr (@Exclude_qrs) {
            if ( $line !~ /$qr/ ) {

               # remember this is AND logic; therefore, one fails means all fail
               $should_exclude = 0;
               last;
            }
         }

         if ($should_exclude) {
            next;
         }
      }

      if (@Match_qrs) {
         my $matched = 1;

         for my $qr (@Match_qrs) {
            if ( $line !~ /$qr/ ) {

              # remember this is AND logic; therefore, one fails means all fail.
               $matched = 0;
               last;
            }
         }

         if ( !$matched ) {
            next;
         }
      }

      my $input_delimiter;
      my @splits;
      my $detail;

      if ( $opt->{GenFixMsg} ) {

         # split a nested fix message into muliple messages

         $detail = parse_fix_message( $line, { %$opt, NestedFix => 1 } );

         my $common = $detail->{common};
         my $comps  = $detail->{components};
         $input_delimiter = $detail->{Delimiter};

         if ( defined $comps ) {
            for my $comp (@$comps) {

               # combine common part and component part

               my $combined_hash;
               %$combined_hash = ( %$common, %$comp );

               push @splits, $combined_hash;
            }
         } else {
            @splits = ($common);
         }
      } else {
         my $ref =
           parse_fix_message( $line, { %$opt, ReturnNestedInArray => 1 } );

         next if !$ref;    # blank line or something not parsable

         # if opt->{NestedFix} is set, ref is a ref to array (of legs)
         # otherwise, it is a ref to a hash of a single order

         if ($NestedFix) {
            @splits = @$ref;
         } else {
            @splits = ($ref);
         }
      }

      my @to_be_assembled
        ;    #GenFixMsg will need this to re-assemble the output message
      my $matched_some_splits;

      for my $r (@splits) {
         if ($FilterExists) {
            my $matched;

            for my $FilterTag (@FilterTags) {
               my $value = $r->{$FilterTag};

               next
                 if !
                 defined $value; # this log line doesn't contain this tag at all

               next
                 if !$FilterExists->{$value}
                 ;               #this log line contain this tag but doesn't
                                 #have the value we wanted
               $matched = 1;
               last;
            }

            next if !$matched;
         }

         if ( $opt->{verbose} ) {
            dump_v_by_k( $r, { %$opt, DumpFH => \*STDERR } );
         }

         next if !$r;

         if ( $matchExps || $excludeExps || $exportExps ) {
            my $old_info;

            if ( $opt->{SourceNewOrder} ) {
               my $OrdID  = $r->{11};
               my $LegID  = $r->{654};
               my $ListID = $r->{66};
               my $tag35  = $r->{35};

               if ( defined($OrdID) ) {
                  if ( defined($LegID) && $tag35 ne 'AB' && $tag35 ne 'AC' ) {
                     $old_info = $OrderInfo->{$OrdID}->{$LegID};

                     if ( !defined $old_info && !$opt->{SourceNewOrderQuiet} ) {
                        carp
"cannot find Multileg order entry for 11=$OrdID,654=$LegID";
                     }
                  } elsif ( defined($ListID) && $tag35 ne 'E' ) {
                     $old_info = $OrderInfo->{$ListID}->{$OrdID};

                     if ( !defined $old_info && !$opt->{SourceNewOrderQuiet} ) {
                        carp "cannot find List entry for 66=$ListID, 11=$OrdID";
                     }
                  } elsif ( $tag35 ne 'D' && $tag35 ne 'F' && $tag35 ne 'G' ) {
                     $old_info = $OrderInfo->{$OrdID};

                     if ( !defined $old_info && !$opt->{SourceNewOrderQuiet} ) {
                        carp "cannot find single order entry for 11=$OrdID";
                     }
                  }
               }
            }

            if ( defined $old_info ) {
               my $combined;

               %$combined = ( %$old_info, %$r );

               TPSUP::Expression::export_var( $combined,
                  { FIX => 1, RESET => 1 } );
            } else {
               TPSUP::Expression::export_var( $r, { FIX => 1, RESET => 1 } );
            }

            if (@tempTags) {
               my $temp_r;

               for ( my $i = 0 ; $i < @tempTags ; $i++ ) {
                  my $c = $tempTags[$i];
                  my $v = $tempExps->[$i]->();

                  $r->{$c}      = $v;
                  $temp_r->{$c} = $v;
               }

               TPSUP::Expression::export_var( $temp_r, { FIX => 1 } )
                 ;    # don't RESET here
            }

            if ( $opt->{verbose} ) {
               TPSUP::Expression::dump_var( { FIX => 1 } );
            }
         }

         if ( $matchExps || $excludeExps ) {
            my $exclude_from_doing;

            if ($excludeExps) {
               for my $e (@$excludeExps) {
                  if ( $e->() ) {
                     $exclude_from_doing++;
                     last;
                  }
               }
            }

            if ($exclude_from_doing) {
               next;
            }

            {
               for my $e (@$matchExps) {
                  if ( !$e->() ) {
                     $exclude_from_doing++;
                     last;
                  }
               }
            }

            if ($exclude_from_doing) {
               next;
            }
         }

         if ( $opt->{verbose} || $opt->{FixPrintMatch} ) {
            print STDERR "matched: $line\n";
            print STDERR dump_v_by_k($r);

            if ( $opt->{SourceNewOrder} ) {
               TPSUP::Expression::dump_var( { FIX => 1 } );
            }
         }

         $matched_some_splits++;

 # when $opt->{GenFixMsg}, only after all legs matched, we increment match_count
         $match_count++ if !$opt->{GenFixMsg};

         if (@exportTags) {
            for ( my $i = 0 ; $i < @exportTags ; $i++ ) {
               my $c = $exportTags[$i];
               $r->{$c} = $exportExps->[$i]->();
            }
         }

         if ( $opt->{GenFixMsg} ) {
            push @to_be_assembled, $r;
         } else {
            push @{ $ref1->{array} }, $r;
         }

         if ( !@OutColumns ) {
            for my $k ( keys %$r ) {
               next if $k !~ /^[0-9a-zA-Z\@_-]+$/;

               $seen_tag->{$k} = 1;
            }
         }
      }

      next if !$matched_some_splits;

      if ( $opt->{GenFixMsg} ) {
         my $message = '';

         my $output_delimiter =
             $opt->{GenFixDelimiter}
           ? $opt->{GenFixDelimiter}
           : $input_delimiter;

         if ( @to_be_assembled != @splits ) {
            next;
         } else {
            $match_count++;

            # for now, if some splits got filterd out, ie
            # @to_be_assembled < @splits;
            # we drop the whole message

            # print the common part
            {
               my $tags = unique_array( [ $detail->{CommTags}, \@exportTags ] );

               my $opt2 = {
                  %$opt,

                  FixDeleteTags => $opt->{GenFixDeleteTags},
                  FixDeleteExp  => $opt->{GenFixDeleteExp},
                  delimiter     => $output_delimiter,
                  tags          => $tags,
               };

               $opt2->{FixFrontTags} =
                   $opt->{GenFixFrontTags}
                 ? $opt->{GenFixFrontTags}
                 : $detail->{CommTags};
               my $submsg = hash_to_fix( $to_be_assembled[0], $opt2 );

               if ($submsg) {
                  if ($message) {
                     $message .= "${output_delimiter}${submsg}";
                  } else {
                     $message = "${submsg}";
                  }
               }
            }

            # print the component part
            for ( my $i = 0 ; $i < @to_be_assembled ; $i++ ) {
               next
                 if !$detail->{CompTagMx}->[$i]
                 || !@{ $detail->{CompTagMx}->[$i] };
               my $opt2 = {
                  %$opt,
                  FixDeleteTags => $opt->{GenFixDeleteTags},
                  FixDeleteExp  => $opt->{GenFixDeleteExp},
                  delimiter     => $output_delimiter,
                  tags          => $detail->{CompTagMx}->[$i],

               };

               $opt2->{FixFrontTags} =
                   $opt->{GenFixFrontTags}
                 ? $opt->{GenFixFrontTags}
                 : $detail->{CompTagMx}->[$i];

               my $submsg = hash_to_fix( $to_be_assembled[$i], $opt2 );

               if ($submsg) {
                  if ($message) {
                     $message .= "${output_delimiter}${submsg}";
                  } else {
                     $message = "${submsg}";
                  }
               }
            }
         }

         if ($out_fh) {
            print {$out_fh} "$message\n";
         }

         if ( $opt->{GenFixReturnMessages} ) {
            push @$ret, $message;
         }
      }

      if ( $out_fh && $opt->{FIXPrintLog} ) {
         print {$out_fh} "$line\n";
      }

      if ( $opt->{FilterFixMaxMatch} ) {
         if (  $opt->{MatchExps}
            || $opt->{ExcludeExps}
            || $opt->{MatchPatterns}
            || $opt->{ExcludePatterns} )
         {
            if ( $match_count >= $opt->{FilterFixMaxMatch} ) {
               last;
            }
         }
      }
   }

   if ( $opt->{ShowProgress} ) {
      my $now = time();

      my $total_sec = $now - $begin_progress_time;

      print STDERR
        "Total $line_count lines are processed in $total_sec seconds.\n";
   }

   if ( !@OutColumns ) {
      @OutColumns = sort( keys %$seen_tag );
   }

   $ref1->{columns} = \@OutColumns;

   my $ref2;

   # use the TPSUP::CSV::query_csv2() engine to massage the output
   if ( !$opt->{GenFixMsg} ) {

      # this block has nothing to do with output (out_fh).
      my $opt2;

      %$opt2 = %$opt;

      $opt2->{InputType} = 'StructuredHash';
      $opt2->{NoPrint}   = 1;
      $opt2->{FIX}       = 1;

      # these switches conflicts with CSV module, so remove them
      # for other csv switch, eg, ReturnKeyedHash, still pass through there
      for my $k (
         qw(output
         ExcludePatterns MatchPatterns
         ExcludeExps     MatchExps
         TempExps        ExportExps)
        )
      {
         delete $opt2->{$k} if exists $opt2->{$k};
      }

      $ref2 = query_csv2( $ref1, $opt2 );

      croak "query_csv2() failed" if $ref2->{status} ne 'OK';

      $ret = $ref2;
   }

   # print_csv_hashArray
   if ( $opt->{RenderOutput} || $PrintCsv ) {
      print_csv_hashArray(
         $ref2->{array},
         $ref2->{columns},
         {
            %$opt,
            delimiter    => $OutDelimiter,
            RenderStdout => $opt->{RenderOutput},
            output       => $opt->{Output},
         }
      );
   }

   close $out_fh if $out_fh && $out_fh != \*STDOUT;

   return $ret;
}

my $front_tags_by_string;
my $is_front_by_string_tag;
my $is_delete_by_string_tag;
my $DeleteExp_by_string;

sub hash_to_fix {
   my ( $href, $opt ) = @_;

   $opt->{verbose} && print STDERR "hash_to_fix() opt=", Dumper($opt);

   my @tags = $opt->{tags} ? @{ $opt->{tags} } : keys(%$href);

   my $allow_tag;
   for my $t (@tags) {
      $allow_tag->{$t} = 1;
   }

   my $front_tags;
   my $is_front;

   my $is_delete;

   my $DeleteExp;

   my $delimiter = defined $opt->{delimiter} ? $opt->{delimiter} : '';

   if ( $opt->{FixFrontTags} ) {
      my $type = ref $opt->{FixFrontTags};

      if ( $type && $type eq 'ARRAY' ) {
         $front_tags = $opt->{FixFrontTags};

         for my $t (@$front_tags) {
            $is_front->{$t} = 1;
         }
      } else {
         my $string = $opt->{FixFrontTags};

         if ( !$front_tags_by_string->{$string} ) {
            @$front_tags = split /,/, $string;

            for my $t (@$front_tags) {
               $is_front_by_string_tag->{$string}->{$t} = 1;
            }
         }

         $is_front = $is_front_by_string_tag->{$string};
      }
   }

   if ( $opt->{FixDeleteTags} ) {
      my $type = ref $opt->{FixDeleteTags};

      if ( $type && $type eq 'ARRAY' ) {
         for my $t ( @{ $opt->{FixDeleteTags} } ) {
            $is_delete->{$t} = 1;
         }
      } else {
         my $string = $opt->{FixDeleteTags};

         if ( !$is_delete_by_string_tag->{$string} ) {
            my @tags = split /,/, $string;

            for my $t (@tags) {
               $is_delete_by_string_tag->{$string}->{$t} = 1;
            }
         }

         $is_delete = $is_delete_by_string_tag->{$string};
      }
   }

   if ( $opt->{FixDeleteExp} ) {
      my $string = $opt->{FixDeleteExp};

# wrap naked $tag in {}, as ${tag}, just like the other variables, eg, ${35}, ${11}
      $string =~ s/\$tag/\${tag}/g;

      if ( !$DeleteExp_by_string->{$string} ) {
         my $warn = $opt->{verbose} ? 'use' : 'no';

         my $converted_string =
           TPSUP::Expression::convert_to_fix_expression( $string, $opt );

         my $compiled = eval
"$warn warnings; no strict; package TPSUP::Expression; sub {my (\$tag, \$fix)=\@_; $converted_string}";

         croak "Bad DeleteExp '$converted_string': $@. converted from $string"
           if $@;

         $DeleteExp_by_string->{$string} = $compiled;
      }

      $DeleteExp = $DeleteExp_by_string->{$string};

      TPSUP::Expression::export_var( $href, { FIX => 1, RESET => 1 } );
   }

   sub test_DeleteExp {
      my ($tag) = @_;

      if ( !defined($DeleteExp) ) {
         return 0;
      }

      my $r;
      $r->{tag} = $tag;

      TPSUP::Expression::export_var( $r, { FIX => 1 } )
        ;    # no RESET here, only overwrite the tag

      #$opt->{verbose} && TPSUP::Expression::dump_var({FIX=>1});

      my $result = $DeleteExp->();

      if ( $result && $opt->{verbose} ) {
         print STDERR "will remove tag=$tag\n";
      }

      return $result;
   }

   my $message;

   for my $tag (@$front_tags) {
      next if !$allow_tag->{$tag};

      next if $is_delete->{$tag};

      next if test_DeleteExp($tag);

      my $value = $href->{$tag};

      next if !defined($value) || !length("$value");

      if ( $tag !~ /^\d+$/ ) {
         my $converted_tag = get_fixtag_by_name( $tag, $opt );

         if ( defined $converted_tag ) {
            next if $is_delete->{$converted_tag};

            next if test_DeleteExp($converted_tag);
            $tag = $converted_tag;
         }

  # if the original cannot be converted to an numeric tag, we print it as it is.
      }

      $message .= "$tag=$value${delimiter}";
   }

   # print the rest tags
   for my $tag (@tags) {
      next if !$allow_tag->{$tag};
      next if $is_front->{$tag};

      next if $is_delete->{$tag};

      next if test_DeleteExp($tag);

      my $value = $href->{$tag};

      next if !defined $value || !length("$value");

      if ( $tag !~ /^\d+$/ ) {
         my $converted_tag = get_fixtag_by_name( $tag, $opt );

         if ( defined $converted_tag ) {
            next if $is_delete->{$converted_tag};

            next if test_DeleteExp($converted_tag);

            $tag = $converted_tag;
         }

  # if the original cannot be converted to an numeric tag, we print it as it is.
      }

      $message .= "$tag=$value${delimiter}";
   }

   my $delimiter_pattern;
   if ( "$delimiter" eq "|" ) {
      $delimiter_pattern = "[$delimiter]";
   } elsif ( "$delimiter" eq '^' || "$delimiter" eq '$' || "$delimiter" eq '?' )
   {
      $delimiter_pattern = "\\$delimiter";
   } else {
      $delimiter_pattern = $delimiter;
   }

   $message =~ s/${delimiter_pattern}$//;    #trim the ending delimiter

   return $message;
}

sub csv_to_fix {
   my ( $csv, $opt ) = @_;

   my $ref;

   {
      my $csv_opt;
      %$csv_opt = %$opt;

      $csv_opt->{ExcludePatterns} = ['^\s*$|^\s*#'];

      $csv_opt->{NoPrint} = 1;

      $opt->{verbose}
        && print "in csv_to_fix() before query_csv2(), csv_opt = ",
        Dumper($csv_opt);

      $ref = query_csv2( $csv, $csv_opt );
   }

   croak "cannot parse $csv" if $ref->{status} ne 'OK';

   $opt->{verbose} && print "in csv_to_fix() after query_csv2(), ref = ",
     Dumper($ref);

   my $out_fh;

   if ( !$opt->{CSV2FIX_NoPrint} ) {
      if ( $opt->{CSV2FIX_0utput} ) {
         $out_fh = get_out_fh( $opt->{CSV2FIX_0utput}, $opt );
      } else {
         $out_fh = \*STDOUT;
      }
   }

   my @messages;
   my $j = 0;

   my $delimiter =
     defined $opt->{CSV2FIX_delimiter} ? $opt->{CSV2FIX_delimiter} : '';
   my $fix_protocol =
     $opt->{CSV2FIX_Protocol} ? $opt->{CSV2FIX_Protocol} : '4.2';

   for my $r ( @{ $ref->{array} } ) {
      $j++;

      my $message;

      if ( !$r->{8} && !$r->{BeginString} ) {
         $message .= "8=FIX.$fix_protocol,";
      }

      $message .= hash_to_fix( $r,
         { %$opt, delimiter => $delimiter, tags => $ref->{columns} } );

      $r->{row} = $j;

      print {$out_fh} $message, "\n" if !$opt->{CSV2FIX_NoPrint};

      push @messages, $message;
   }

   close $out_fh if $out_fh && $out_fh != \*STDOUT;

   return \@messages;
}

sub diff_fix {
   my ( $inputs, $RefMatrix, $opt ) = @_;

   my $out_fh;

   if ( $opt->{DiffFixOutput} ) {
      $out_fh = get_out_fh( $opt->{DiffFixOutput}, $opt );
      croak "cannot write to output $opt->{Output}" if !$out_fh;
   }

   my $num_input = scalar(@$inputs);

   my $fixs;
   my @TagMatrix;

   for ( my $i = 0 ; $i < $num_input ; $i++ ) {
      my $opt2 = {
         %$opt,
         ReturnKeyedHash => $RefMatrix->[$i],
         NoColumnChecks  => 1,
      };

      my $ref = filter_fix( $inputs->[$i], $opt2 );

      if ( !$ref ) {
         croak "failed to parse input->[$i]";
      }

      if ( $ref->{status} ne 'OK' ) {
         print STDERR "input->[$i] = ", Dumper($ref);
         croak "failed to parse input->[$i]";
      }

      $fixs->[$i] = $ref->{KeyedHash};

      push @TagMatrix, $ref->{columns};

      $opt->{verbose} && print STDERR "fixs->[$i] = ", Dumper( $fixs->[$i] );
   }

   my $cmp_tags;

   if ( $opt->{DiffFixCmpTags} ) {
      $cmp_tags = $opt->{DiffFixCmpTags};
   } else {
      $cmp_tags = sort_unique( \@TagMatrix, { SortUniqueNumeric => 1 } );
   }

   my @keyMatrix;

   for ( my $i = 0 ; $i < $num_input ; $i++ ) {
      my @a = keys %{ $fixs->[$i] };
      push @keyMatrix, \@a;
   }

   my $keys = sort_unique( \@keyMatrix );

   my $width = 30;

   for my $k (@$keys) {
      my $max_num_rows = 0;

      for ( my $i = 0 ; $i < $num_input ; $i++ ) {
         if ( $fixs->[$i]->{$k} ) {
            my $num_rows = scalar( @{ $fixs->[$i]->{$k} } );

            if ( $max_num_rows < $num_rows ) {
               $max_num_rows = $num_rows;
            }
         }
      }

      for ( my $j = 0 ; $j < $max_num_rows ; $j++ ) {
         my $row_num = $j + 1;

         my $prefix = "key=$k row=$row_num of $max_num_rows";

         my $one_missing_key;

         for ( my $i = 0 ; $i < $num_input ; $i++ ) {
            if ( !$fixs->[$i]->{$k}->[$j] ) {
               print {$out_fh}
                 "$prefix: input->[$i] missing whole row $row_num\n\n"
                 if $out_fh;

               $one_missing_key++;
               last;
            }
         }

         next if $one_missing_key;

         my $block;

         my $num_mismatch = 0;

         for my $tag (@$cmp_tags) {
            my $line;

            my $mismatched;
            my $last_value;

            for ( my $i = 0 ; $i < $num_input ; $i++ ) {
               my $current_value = $fixs->[$i]->{$k}->[$j]->{$tag};

               if ( !defined $current_value ) {
                  if ( defined $last_value ) {
                     $mismatched++;
                     $num_mismatch++;
                     last;
                  }
               }

               if ( !defined $last_value ) {
                  if ( $i != 0 ) {
                     $mismatched++;
                     $num_mismatch++;
                     last;
                  }

                  $last_value = $current_value;
               } elsif ( "$last_value" ne "$current_value" ) {
                  $mismatched++;
                  $num_mismatch++;
                  last;
               }
            }

            next if !$mismatched && !$opt->{verbose};

            my $name = get_fixname_by_tag($tag);

            $name = '' if !defined $name;

            my $left .= sprintf( "%s %3s", $name, "$tag" );

            if ( $opt->{verbose} ) {
               my $w2 = $width - 1;    # use the first char as diff indicator

               if ($mismatched) {
                  $line .= 'x';
               } else {
                  $line .= '=';
               }

               $line .= sprintf( "\%${w2}s", "$left |" );
            } else {
               $line .= sprintf( "\%${width}s", "$left |" );
            }

            for ( my $i = 0 ; $i < $num_input ; $i++ ) {
               my $string;

               my $v = $fixs->[$i]->{$k}->[$j]->{$tag};

               if ( !$v ) {
                  $string = '';
               } else {
                  $string = "$v";

                  my $size = length($string);

                  if ( $size < $width ) {
                     my $desc = get_desc_by_tag_value( $tag, $v );

                     if ($desc) {
                        if ( length($desc) > $width - $size - 3 ) {
                           my $sub_desc =
                             substr( $desc, 0, $width - $size - 3 );
                           $string .= " ($sub_desc)";
                        } else {
                           $string .= " ($desc)";
                        }
                     }
                  }
               }

               if ( $i < $num_input - 1 ) {

                  # add a separator pipe if not the last column
                  $line .= sprintf( "\%${width}s", "$string |" );
               } else {
                  $line .= sprintf( "\%${width}s", $string );
               }
            }

            $block .= "$line\n";
         }

         if ( $num_mismatch || $opt->{verbose} ) {
            my $header = "$prefix: $num_mismatch tag(s) mismatched\n";
            $header .= '-' x ( $width - 1 ) . '+';

            for ( my $i = 0 ; $i < $num_input ; $i++ ) {
               $header .= '-' x ( $width - 1 );

               if ( $i < $num_input - 1 ) {
                  $header .= '+';
               }
            }

            print {$out_fh} "$header\n$block\n\n" if $out_fh;
         } else {
            $block = "$prefix: all matched\n$block";
            print {$out_fh} "$block\n\n" if $opt->{verbose} && $out_fh;
         }
      }
   }

   close $out_fh if $out_fh && $out_fh != \*STDOUT;
}

1
