namespace sprite
{
  inline Walk walk(Cursor root) { return Walk(root); }
  inline Walk2 walk(Cursor root, void * static_data, datadisposer_type disposer)
    { return Walk2(root, static_data, disposer); }
  inline Walk::Walk(Cursor root) : stack({Level{root}}) { assert(root); }
  inline Walk::operator bool() const { return !this->stack.empty(); }
  inline Cursor Walk::cursor() const
    { assert(*this); return this->stack.back().cur; }
  inline void Walk::extend()
  {
    Level & parent = stack.back();
    parent.index = NOINDEX;
    parent.end = parent.cur.kind == 'p' ? parent.cur->info->arity : 0;
    this->stack.emplace_back();
  }
  inline Walk2::Walk2(Cursor root, void * static_data, datadisposer_type dispose)
    : stack({Level{root}}), static_data(static_data), dispose(dispose)
    { assert(root); }
  inline Walk2::operator bool() const { return !this->stack.empty(); }
  inline void Walk2::extend(void * data)
  {
    Level & parent = stack.back();
    parent.index = NOINDEX;
    parent.end = parent.cur.kind == 'p' ? parent.cur->info->arity : 0;
    this->stack.emplace_back(data);
  }
  inline Cursor Walk2::cursor() const
  {
    assert(*this);
    return this->stack.back().cur;
  }
  inline void *& Walk2::data() const
  {
    assert(*this);
    return this->stack.back().data;
  }
}
