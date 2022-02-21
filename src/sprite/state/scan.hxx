namespace sprite
{
  inline Scan::Scan(Cursor root)
    : search({Level{root}}), callstack(1)
  {
    assert(root);
  }

  inline void Scan::reset()
  {
    if(this->search.size() > 1)
      this->search.resize(1);
  }

  inline Scan::operator bool() const
  {
    return this->search.size() > this->callstack.back();
  }

  inline void Scan::extend()
  {
    Level & parent = search.back();
    parent.index = NOINDEX;
    parent.end = parent.cur.kind == 'p' ? parent.cur->info->arity : 0;
    this->search.emplace_back();
  }

  inline void Scan::pop()
  {
    size_t ret = this->callstack.back();
    this->search.resize(ret);
    this->callstack.pop_back();
  }

  inline Cursor Scan::cursor() const
  {
    assert(*this);
    return this->search.back().cur;
  }

  inline size_t Scan::size() const { return this->search.size(); }
  inline void Scan::resize(size_t n) { this->search.resize(n); }

  inline Node * Scan::copy_spine(Node * root, Node * end, size_t start)
  {
    return this->copy_spine(root, end, nullptr, start);
  }
}
