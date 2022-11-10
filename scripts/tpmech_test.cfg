#!/usr/bin/env perl

use strict;
use warnings;
use TPSUP::MECHANIZE qw();

# 'our' can be used multiple times. Using it here allows us to use 'strict' and 'warning'
# to check this cfg file alone, as
#     $ perl tpslnm_test.cfg

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   resources => {
      mechanize => {
         method => \&TPSUP::MECHANIZE::get_mech,
         cfg => {
         },
         # enabled => 1,   # default is enabled.
      },
   },

   # position_args will be inserted into $opt hash to pass forward
   # position_args => [],

   pre_checks => [
      # you need this in corporate network
      #{ 
      #   check      => 'exists($ENV{HTTPS_CA_DIR})',
      #   suggestion => 'run: export HTTPS_CA_DIR=/etc/ssl/certs',
      #},
   ],

   usage_example => <<'END',

   linux1$ {{prog}} s=tian
   linux1$ {{prog}} s=editor

END

   # all keys in keys, suits and aliases should be upper case
   # this way so that user can use case-insensitive keys on command line
   keys => {
      NAME  =>  undef, 
      ENTRY =>  undef, 
   },

   suits => {
      tian => {
         NAME => 'Tianhua Han',
         ENTRY => 'lca_tian',
      },

      editor => {
         NAME => 'LCA Editor Tester',
         ENTRY => 'lca_editor',
      },
   },

   aliases => {
      n => 'NAME',
      e => 'ENTRY',
   },
};

use TPSUP::LOCK qw(get_entry_by_key);
use HTML::TreeBuilder qw();

sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $verbose = $opt->{verbose};

   my $entry_key = $known->{ENTRY};
   my $entry = get_entry_by_key($entry_key);
   die "get_entry_by_key($entry_key}) failed" if !$entry;

   my $username = $entry->{user};
   my $password = $entry->{decoded};

   my $mech = $all_cfg->{resources}->{mechanize}->{driver};

   my $login_url = "https://www.livingstonchinese.org/LCA2";

   $mech-> get($login_url);

   my $need_to_login = 1;
   if ( $mech->content() =~ /login-greeting/) {
      print "already logged in\n";

      if ($mech->content() =~ /Hi $known->{NAME}/) {
         print "logged in as $known->{NAME}, correct user\n";
         $need_to_login = 0;
      } else {
         print "logged in as wrong user. logging out\n";
         $need_to_login = 1;

         #<div class="logout-button">
         #   <input type="submit" name="Submit" class="btn btn-primary" value="Log out">
         #die "login-form not found" if !$mech->form_id('login-form');
         $mech->submit_form(
             form_id => 'login-form',
         );

      } 
   }

   if ($need_to_login) {
      print "sending login/password\n";

      # <form action="https://www.livingstonchinese.org/LCA2/index.php/component/users/?Itemid=103" method="post" id="login-form" class="form-inline">
      #  <div id="form-login-username" class="control-group">
      #    <input id="modlgn-username" type="text" name="username" class="input-small" tabindex="0" size="18" placeholder="Username" />
      #  <div id="form-login-password" class="control-group">
      #     <input id="modlgn-passwd" type="password" name="password" class="input-small" tabindex="0" size="18" placeholder="Password" />
      #  <button type="submit" tabindex="0" name="Submit" class="btn btn-primary login-button">Log in</button>
  
      $mech->submit_form(
         form_id => 'login-form',
         fields  => {
            # these are actually 'name' attr, not 'id' attr!!!
            'username' => $username,
            'password' => $password,
         },
      );
   
      my $content = $mech->content();
      if ($verbose) {
         print Encode::encode('utf8', $content);
      } else {
         print "got content\n";
      }
   }
 
   $verbose && print "cookies = ", $mech->cookie_jar->as_string(), "\n";

   $mech->follow_link(text => 'My Account');

   {
      my $content = $mech->content();

      # <fieldset id="users-profile-core">
      # 	<legend>
      # 		Profile	</legend>
      # 	<dl class="dl-horizontal">
      # 		<dt> Name	</dt> <dd> Tian		</dd>
      # 		<dt> Username	</dt> <dd> tian@homedepot.com	</dd>
      # 		<dt> Registered Date	</dt> <dd> Friday, 15 May 2020	</dd>
      # 		<dt> Last Visited Date	</dt> <dd> Monday, 21 February 2022</dd>
      # 	</dl>
      # </fieldset>

      my $tree=HTML::TreeBuilder->new_from_content($content);
      
      # https://perlmaven.com/web-scraping-with-html-treebuilder
      # https://metacpan.org/pod/HTML::Element#look_down
      my $fieldset = $tree->look_down('id', 'users-profile-core');
      my $text = $fieldset->as_text;
      print "$text\n";

      if ($verbose) {
         print Encode::encode('utf8', $content);
      } else {
         print "got content\n";
      }
   }
}
