our $our_syntax = {
   '^/$' => {
      'cfg'          => { 'type' => 'HASH', 'required' => 1 },
      'package'      => { 'type' => 'SCALAR' },
      'minimal_args' => { 'type' => 'SCALAR' },
      'extra_args'   => { 'type' => 'HASH' },
      'pre_checks'   => { 'type' => 'ARRAY' },
   },

   # non-greedy match
   # note: don't use ^/cfg/(.+?)/$, because it will match /cfg/abc/def/ghi/, not only /cfg/abc/
   '^/cfg/([^/]+?)/$' => {
      'base_urls'  => { 'type' => 'ARRAY', 'required' => 1 },
      'op'         => { 'type' => 'HASH',  'required' => 1 },
      'entry'      => { 'type' => [ 'SCALAR', 'CODE' ] },
      'entry_func' => { 'type' => 'CODE' },
   },
   '^/cfg/([^/]+?)/op/([^/]+?)/$' => {
      'sub_url'   => { 'type' => 'SCALAR', 'required' => 1 },
      'num_args'  => { 'type' => 'SCALAR', 'pattern'  => qr/^\d+$/ },
      'json'      => { 'type' => 'SCALAR', 'pattern'  => qr/^\d+$/ },
      'method'    => { 'type' => 'SCALAR', 'pattern'  => qr/^(GET|POST|DELETE)$/ },
      'Accept'    => { 'type' => 'SCALAR' },
      'comment'   => { 'type' => 'SCALAR' },
      'validator' => { 'type' => [ 'SCALAR', 'CODE' ] },
      'post_data' => { 'type' => 'SCALAR' },
      'test_str'  => { 'type' => 'ARRAY' },
   },
};
