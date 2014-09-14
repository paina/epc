#!/usr/bin/perl -T

# Input SGTIN (Serialized Global Trade Item Number) and convert it into a barcode on a web URL.
# Spec of SGTIN: http://www.gs1.org/gsmp/kc/epcglobal/tds/tds_1_3-standard-20060308.pdf , pp.12-

# Copyright SATO Taisuke / Auto-ID Lab. Japan 2013

=license

Copyright (c) 2013, SATO Taisuke <paina@sfc.wide.ad.jp>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

=cut

use strict;
use warnings;

use Barcode::Code128 qw(FNC1);
use CGI;
use GD;

# output error message as a PNG file and exit.
sub err ($) {
  my $mesg = shift;
  $mesg = "<ERROR> ".$mesg;

  my $image = GD::Image->new(500,20)
    or die "Cannot new GD.";

  my $white = $image->colorAllocate(255,255,255);
  my $red = $image->colorAllocate(255,0,0);
  $image->string(gdSmallFont, 5, 5, $mesg, $red);
  print $image->png;

  exit;
}

# parse pure identity and store data into a hash.
sub parse_pi ($) {
  my $pi = shift;
  $pi =~ /^urn:epc:id:sgtin:(\d+)\.(\d+).(\d+)$/
    or err "invalid SGTIN pure identity.";

  unless (length($1) + length($2) == 13) {
    err "Total number of digits in company prefix and item reference must be 13";
  }

  unless (substr($2, 0, 1) eq "0" || substr($2, 0, 1) eq "1") {
    err "First digit of item reference must be 0 or 1";
  }

  my $sgtin =  { company => $1,    # Company prefix
		 item    => $2,    # Item reference
		 serial  => $3 };  # Serial number

  return $sgtin;
}

# calc check digit.
sub calc_cd ($) {
  my $part = shift; # GTIN string without check digit

  my @digit = split(//, $part);
  my $sum = 0;
  my $i = 0;

  unless (scalar(@digit) == 13) {
    err "GTIN part without check digit is not 13 digits.";
  }

  #        | (13) (12) (11) .. ( 1)
  # @digit | [ 0] [ 1] [ 2] .. [12]
  #        |  x3        x3      x3
  # -------+-------------------------
  #   $sum =  XX + XX + XX  ..  XX

  foreach (@digit) {
    if ($i % 2 == 0) {
      $sum += $_ * 3;
    } else {
      $sum += $_;
    }
    $i++;
  }

  my $cd = 10 - ($sum % 10);
  $cd = 0 if ($cd == 10);

  return $cd;
}

# Calc GTIN number from a hash of SGTIN data.
sub gtin ($) {
  my $sgtin = shift;

  $sgtin->{item} =~ /^(\d)(\d+)$/;
  my $pack = $1;
  my $remain = $2;

  my $part = $pack.$sgtin->{company}.$remain;
  my $cd = calc_cd($part);
  my $gtin = $part.$cd;

  return $gtin;
}

# Convert a hash of SGTIN data into barcode string.
sub barcode ($) {
  my $sgtin = shift;

  my $gtin = gtin($sgtin);
  my $barcode = '(01)'.$gtin.'(21)'.$sgtin->{serial};

  return $barcode;
}

# Return PNG image of barcode.
sub image ($) {
  my $text = shift;
  my $code = new Barcode::Code128;

  my $numbers = $text;
  $numbers =~ s/[\(\)]//g;

  $code->code('C');
  $code->show_text(1);
  $code->border(0);
  $code->scale(2);
  $code->encode(FNC1.$numbers, 'C');
  $code->text($text);
  $code->font_align('center');

  return png $code;
}

### main

my $cgi = new CGI or die "Cannot new CGI";
print $cgi->header( -type => 'image/png' );

binmode STDOUT;

err "No SGTIN specified" unless (exists $ENV{PATH_INFO});
err "PATH_INFO invalid" unless ($ENV{PATH_INFO} =~ /\/(.*)$/);

my $input = $1;
my $text;

if      ( $input =~ /^urn:epc:id:sgtin:(\d+)\.(\d+).(\d+)$/ ) { # SGTIN pure identity format
  $text = barcode(parse_pi($input));
} elsif ( $input =~ /^[0-9\(\)]+$/ ) { # enumeration of numbers, '(' and ')'
                                       # WARN: no format validation
  $text = $input;
} else {
  err "invalid SGTIN or numbers";
}

print image($text);
